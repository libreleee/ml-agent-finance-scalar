# Trino + Iceberg + SeaweedFS(S3) 기동 실패 및 메타데이터 오류 (Bugfix 기록)

## 개요

로컬 환경에서 Trino + Iceberg + SeaweedFS(S3) 연동 중 다음 문제가 연쇄적으로 발생하였다.

- Trino 서버가 기동되지 않거나 오래 “starting” 상태에서 벗어나지 않음
- Iceberg 테이블 조회 시 `ICEBERG_INVALID_METADATA` 발생
- Trino에서 `DROP TABLE` 수행 시 S3 경로 삭제 실패

이 문서는 증상/원인/조치/조치방법을 상세히 기록한다.

---

## 1) 증상

### 1.1 Trino가 오래 초기화 중(starting) 상태

- Trino CLI에서 쿼리 실행 시:
  - `Trino server is still initializing`
- 로그에서 반복:
  - `Error fetching memory info ... returned status 503`

### 1.2 Trino가 부팅에 실패하거나 재시작 반복

- 로그에 아래 에러:
  - `Configuration property 'hive.s3.*' was not used`
  - `Configuration property 's3.*' was not used`
- Trino 컨테이너 상태:
  - `Exited (100)` 또는 `unhealthy`

### 1.3 Iceberg 테이블 조회 실패

- `SELECT * FROM iceberg.logs_db.raw_logs LIMIT 10;`
  - `ICEBERG_INVALID_METADATA`

### 1.4 `DROP TABLE` 실패

- `DROP TABLE iceberg.logs_db.raw_logs;`
  - `Failed to delete directory s3a://lakehouse/warehouse/logs_db.db/raw_logs`

---

## 2) 원인

### 2.1 S3 설정 위치 오류 (Trino 479 기준)

- Trino 479에서는 Iceberg 카탈로그 파일에 `hive.s3.*` 또는 `s3.*` 속성을 직접 넣으면 **미사용 속성으로 간주**되고 부팅 실패.
- S3 설정은 **filesystem 레벨 설정**으로 분리해야 함:
  - `fs.native-s3.enabled=true`는 카탈로그에 유지
  - 실제 S3 접속 설정은 `/etc/trino/filesystem/s3.properties`로 이동

### 2.2 AWS Region 누락

- Trino 내부 AWS SDK가 Region을 찾지 못해 부팅 실패:
  - `SdkClientException: Unable to load region ...`
- 로컬/호환 S3라도 Region은 필수.

### 2.3 Iceberg 메타데이터 불일치

- 초기에는 Spark에서 `hadoop` 카탈로그로 Iceberg 테이블 생성.
- 이후 Trino/Superset 접근을 위해 `hive` 카탈로그로 전환.
- 이 과정에서 기존 S3 메타데이터(warehouse path)가 남아 있어 **메타데이터 불일치** 발생.

### 2.4 S3 객체 삭제 실패로 인한 DROP TABLE 실패

- Trino `DROP TABLE`은 S3에 있는 테이블 경로 삭제를 포함.
- SeaweedFS 객체 삭제 실패 시 `DROP TABLE` 자체가 실패.

---

## 3) 조치 내용

### 3.1 Trino 카탈로그/파일시스템 설정 분리

**파일:** `trino-config/catalog/iceberg.properties`

```
connector.name=iceberg
iceberg.catalog.type=hive_metastore
hive.metastore.uri=thrift://hive-metastore:9083
iceberg.file-format=PARQUET
fs.native-s3.enabled=true
```

**신규 파일:** `trino-config/filesystem/s3.properties`

```
s3.endpoint=http://seaweedfs-s3:8333
s3.aws-access-key=seaweedfs_access_key
s3.aws-secret-key=seaweedfs_secret_key
s3.path-style-access=true
s3.ssl.enabled=false
s3.region=us-east-1
```

### 3.2 Trino 환경변수로 Region 및 키 강제

**파일:** `docker-compose.yml`

```
environment:
  AWS_REGION: us-east-1
  AWS_ACCESS_KEY_ID: seaweedfs_access_key
  AWS_SECRET_ACCESS_KEY: seaweedfs_secret_key
```

### 3.3 Iceberg 메타데이터 정리

- S3에 남아있던 메타데이터 경로 삭제:
  - `s3a://lakehouse/warehouse/logs_db.db/raw_logs/`
- boto3로 prefix 삭제 수행

### 3.4 테이블 재생성

- `DROP TABLE` 시도 후 실패 → S3 경로 수동 삭제 → `DROP TABLE` 재시도
- 이후 `python/fspark_raw_examples.py`로 테이블 재생성

---

## 4) 조치 방법 (재현/복구 절차)

### 4.1 Trino 설정 적용 및 재기동

```bash
docker compose restart trino
```

### 4.2 테이블 DROP 실패 시 S3 경로 수동 삭제

**사전:** Python 환경에 boto3 설치 필요

```bash
.venv/bin/python -m ensurepip
.venv/bin/python -m pip install boto3
```

**삭제 스크립트:**

```bash
.venv/bin/python - <<'PY'
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:8333",
    aws_access_key_id="seaweedfs_access_key",
    aws_secret_access_key="seaweedfs_secret_key",
    region_name="us-east-1",
)

bucket = "lakehouse"
prefix = "warehouse/logs_db.db/raw_logs/"

paginator = s3.get_paginator("list_objects_v2")
to_delete = []
count = 0

for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
    for obj in page.get("Contents", []):
        to_delete.append({"Key": obj["Key"]})
        count += 1
        if len(to_delete) == 1000:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})
            to_delete = []

if to_delete:
    s3.delete_objects(Bucket=bucket, Delete={"Objects": to_delete})

print(f"deleted {count} objects under {prefix}")
PY
```

### 4.3 테이블 재생성

```sql
DROP TABLE iceberg.logs_db.raw_logs;
```

```bash
python python/fspark_raw_examples.py
```

```sql
SELECT * FROM iceberg.logs_db.raw_logs LIMIT 10;
```

---

## 5) 재발 방지 체크리스트

- [ ] Trino 479 이상에서는 S3 설정을 `filesystem/s3.properties`로 분리
- [ ] `fs.native-s3.enabled=true` 유지
- [ ] `AWS_REGION` 반드시 설정
- [ ] 카탈로그 타입 변경 시 (hadoop → hive) 기존 S3 메타데이터 정리
- [ ] DROP TABLE 실패 시 S3 경로 수동 삭제 필요 여부 확인

---

## 참고

- Trino S3 Filesystem docs:
  - https://trino.io/docs/current/object-storage/file-system-s3.html
