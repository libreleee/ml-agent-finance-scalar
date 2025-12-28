# Bugfix: Spark S3A NumberFormatException ("60s", "30s", "24h")

## 일시
2025-12-23

## 증상
Spark 4.1.0 환경에서 Iceberg/S3A 파일시스템 초기화 중 다음과 같은 에러 발생하며 중단됨:
`java.lang.NumberFormatException: For input string: "60s"` (또는 "30s", "24h")

## 원인
1. **Hadoop 기본값 파싱 오류**: Spark 4.1.0에 포함된 Hadoop 3.4.2의 `core-default.xml`에는 `fs.s3a.connection.timeout` 등이 "60s"와 같이 단위가 포함된 문자열로 정의되어 있음. 특정 코드 경로에서 이를 순수 정수로 파싱하려 시도하면서 에러 발생.
2. **버킷 부재**: SeaweedFS S3 게이트웨이에 `lakehouse` 버킷이 생성되어 있지 않아 `NoSuchBucket` 에러 발생.
3. **인증 설정 오류**: `docker-compose.yml`에서 SeaweedFS S3 인증 변수가 `S3_ACCESS_KEY`로 되어 있어 Spark의 서명된 요청(Signed Request) 검증에 실패함.

## 조치 사항

### 1. Spark 설정 오버라이드 (python/fspark.py)
단위가 포함된 문자열 설정을 순수 숫자(밀리초 또는 초)로 명시적으로 덮어씀.
- `fs.s3a.connection.timeout`: "60000"
- `fs.s3a.socket.timeout`: "60000"
- `fs.s3a.threads.keepalivetime`: "60000"
- `fs.s3a.connection.establish.timeout`: "60000"
- `fs.s3a.multipart.purge.age`: "86400"
- `hadoop.service.shutdown.timeout`: "30000"

### 2. SeaweedFS S3 인증 수정 (docker-compose.yml)
환경 변수명을 `AWS_ACCESS_KEY_ID` 및 `AWS_SECRET_ACCESS_KEY`로 변경하여 표준 호환성 확보.

### 3. 버킷 생성
`aws-cli`를 사용하여 `lakehouse` 버킷 수동 생성.

## 수정 내용 (Before & After)

### [python/fspark.py](python/fspark.py)
**수정 전:**
```python
    .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.socket.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.attempts.maximum", "3") \
```

**수정 후:**
```python
    .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.socket.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.threads.keepalivetime", "60000") \
    .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.multipart.purge.age", "86400") \
    .config("spark.hadoop.hadoop.service.shutdown.timeout", "30000") \
    .config("spark.hadoop.fs.s3a.attempts.maximum", "3") \
```

### [docker-compose.yml](docker-compose.yml)
**수정 전:**
```yaml
    environment:
      S3_ACCESS_KEY: seaweedfs_access_key
      S3_SECRET_KEY: seaweedfs_secret_key
```

**수정 후:**
```yaml
    environment:
      AWS_ACCESS_KEY_ID: seaweedfs_access_key
      AWS_SECRET_ACCESS_KEY: seaweedfs_secret_key
```
