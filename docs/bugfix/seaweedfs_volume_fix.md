# SeaweedFS Volume 컨테이너 종료 및 데이터 적재 오류 수정

## 1. 증상 (Symptom)
- `seaweedfs-volume` 컨테이너가 실행 직후 **Exit Code 255**로 종료됨.
- 로그 확인 시 `stat /data/volume: no such file or directory` 에러 발생.
- Streamlit 등 클라이언트에서 S3 업로드/다운로드 시 `404 Not Found` 또는 `Connection refused` 에러 발생.
- `scripts/lakehouse_infra.sh` 실행 시 터미널이 멈추거나(Foreground), 중단 시 컨테이너가 함께 종료됨.

## 2. 원인 (Cause)
1.  **데이터 디렉토리 경로 불일치**: `seaweedfs-volume` 실행 명령어가 `-dir=/data/volume`으로 설정되어 있었으나, 실제 마운트된 볼륨 경로는 `/data`였음. 컨테이너 시작 시 해당 하위 디렉토리가 존재하지 않아 프로세스가 종료됨.
2.  **포트 설정 혼선**: 내부 포트가 8080으로 설정되어 있어 로그 분석 시 Trino(8080)와 혼동될 여지가 있었으며, 명시적인 포트 지정이 누락됨.
3.  **스크립트 실행 모드**: 인프라 실행 스크립트에서 `-d` (Detached mode) 옵션이 누락되어 터미널 세션 종속적인 실행이 됨.

## 3. 조치 (Action)
1.  `docker-compose.yml` 수정:
    - `seaweedfs-volume`의 데이터 디렉토리를 `-dir=/data`로 변경.
    - 내부 포트를 `8081`로 변경하고 명시적으로 지정.
    - Healthcheck 포트도 `8081`로 수정.
2.  `scripts/lakehouse_infra.sh` 수정:
    - `docker compose up` 명령어에 `-d` 옵션 추가.
3.  데이터 초기화:
    - 기존 꼬인 메타데이터 제거를 위해 `docker compose down -v` 수행 후 재시작.

## 4. 수정 내역 (Code Changes)

### 1) docker-compose.yml

**파일 위치**: `/home/i/work/ai/lakehouse-tick/docker-compose.yml`
**수정 라인**: 48-57 (약)

**수정 전 (Before)**
```yaml
  seaweedfs-volume:
    image: chrislusf/seaweedfs:4.02
    container_name: seaweedfs-volume
    ports:
      - "8081:8080"
    command: ["volume", "-mserver=seaweedfs-master:9333", "-ip.bind=0.0.0.0", "-ip=seaweedfs-volume", "-dir=/data/volume"]
    # ...
    healthcheck:
      test: ["CMD", "true"]
```

**수정 후 (After)**
```yaml
  seaweedfs-volume:
    image: chrislusf/seaweedfs:4.02
    container_name: seaweedfs-volume
    ports:
      - "8081:8081"
    command: ["volume", "-mserver=seaweedfs-master:9333", "-ip.bind=0.0.0.0", "-ip=seaweedfs-volume", "-port=8081", "-dir=/data"]
    # ...
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "8081"]
```

### 2) scripts/lakehouse_infra.sh

**파일 위치**: `/home/i/work/ai/lakehouse-tick/scripts/lakehouse_infra.sh`
**수정 라인**: 9

**수정 전 (Before)**
```bash
docker compose up seaweedfs-master seaweedfs-volume seaweedfs-filer seaweedfs-s3 postgres hive-metastore spark-iceberg trino
```

**수정 후 (After)**
```bash
docker compose up -d seaweedfs-master seaweedfs-volume seaweedfs-filer seaweedfs-s3 postgres hive-metastore spark-iceberg trino
```