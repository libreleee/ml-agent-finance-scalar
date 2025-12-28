# Airflow 및 Lakehouse 파이프라인 트러블슈팅 리포트

**작성일:** 2025-12-28
**작성자:** Gemini Code Assist
**대상 시스템:** Airflow (MLOps), Spark (Data Init), Visual Stack

---

## 1. Airflow DAG 실행 실패 (라이브러리 미설치)

### 증상 (Symptoms)
- Airflow DAG (`ml_pipeline_end_to_end`) 실행 시 `ModuleNotFoundError: No module named 'mlflow'` 등의 에러 발생.
- 태스크가 실행되지 않고 즉시 실패함.

### 원인 (Cause)
- Airflow Worker 및 Scheduler 컨테이너 환경에 DAG 실행에 필요한 Python 라이브러리(`mlflow`, `scikit-learn`, `numpy`, `boto3`)가 설치되어 있지 않음.

### 조치 (Action)
- `docker-compose-mlops.yml` 파일의 `_PIP_ADDITIONAL_REQUIREMENTS` 환경 변수에 필요한 패키지 목록을 추가하여 컨테이너 시작 시 자동 설치되도록 설정.

### 상세 수정 내역
**파일:** `docker-compose-mlops.yml`

```yaml
# 수정 전 (airflow-webserver, scheduler, worker 공통)
_PIP_ADDITIONAL_REQUIREMENTS: mlflow scikit-learn numpy

# 수정 후
_PIP_ADDITIONAL_REQUIREMENTS: mlflow boto3 scikit-learn numpy
```

---

## 2. S3 연결 및 모델 아티팩트 저장 실패

### 증상 (Symptoms)
- `model_training` 태스크가 `up_for_retry` 상태로 멈추거나 실패함.
- MLflow UI에서 모델 아티팩트가 보이지 않음.
- 로그에 S3 연결 타임아웃 또는 AWS 인증 오류 발생 가능성.

### 원인 (Cause)
- `boto3` 라이브러리가 로컬 SeaweedFS S3(`http://seaweedfs-s3:8333`)가 아닌 실제 AWS S3로 연결을 시도함.
- `AWS_ENDPOINT_URL` 환경 변수가 누락되어 엔드포인트 리다이렉션이 발생하지 않음.

### 조치 (Action)
- Airflow 서비스(`webserver`, `scheduler`, `worker`) 및 `mlflow` 서비스에 S3 관련 환경 변수(`AWS_ENDPOINT_URL`, `MLFLOW_S3_ENDPOINT_URL`, `AWS_REGION`)를 명시적으로 추가.

### 상세 수정 내역
**파일:** `docker-compose-mlops.yml`

```yaml
# 수정 전 (airflow-worker 예시)
environment:
  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-seaweedfs_access_key}
  AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-seaweedfs_secret_key}
  AWS_ENDPOINT_URL_S3: http://seaweedfs-s3:8333
  MLFLOW_S3_ENDPOINT_URL: http://seaweedfs-s3:8333
  AWS_REGION: us-east-1

# 수정 후
environment:
  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-seaweedfs_access_key}
  AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-seaweedfs_secret_key}
  AWS_ENDPOINT_URL_S3: http://seaweedfs-s3:8333
  AWS_ENDPOINT_URL: http://seaweedfs-s3:8333  # 추가: boto3 표준 엔드포인트
  MLFLOW_S3_ENDPOINT_URL: http://seaweedfs-s3:8333
  AWS_REGION: us-east-1
  AWS_DEFAULT_REGION: us-east-1 # 추가
```

---

## 3. Spark 데이터 초기화 오류 (Schema Mismatch & Table Missing)

### 증상 (Symptoms)
- **증상 A:** `fspark_raw_examples.py` 실행 시 `AnalysisException: Cannot safely cast file_size STRING to BIGINT` 에러 발생.
- **증상 B:** Streamlit 앱 실행 시 `NoSuchTableError: Table does not exists: image_metadata` 에러 발생.

### 원인 (Cause)
- **원인 A:** `spark.createDataFrame` 사용 시 딕셔너리 키 정렬로 인해 데이터프레임 컬럼 순서가 알파벳순으로 변경되었으나, `insertInto`는 위치 기반으로 매핑하여 타입 불일치 발생.
- **원인 B:** 초기화 스크립트에 `media_db.image_metadata` 테이블을 생성하는 DDL 구문이 누락됨.

### 조치 (Action)
- **조치 A:** 데이터프레임을 테이블 스키마 순서대로 `.select()` 하여 정렬.
- **조치 B:** `CREATE TABLE IF NOT EXISTS` 구문 추가.

### 상세 수정 내역
**파일:** `python/fspark_raw_examples.py`

**수정 A (컬럼 정렬):**
```python
# 수정 전
df_images = spark.createDataFrame(image_meta_rows)
df_images.write.mode("append").insertInto("hive_prod.media_db.image_metadata")

# 수정 후
df_images = spark.createDataFrame(image_meta_rows)
# 테이블 스키마 순서에 맞춰 컬럼 정렬 (insertInto는 위치 기반 매핑)
df_images = df_images.select("image_id", "s3_path", "file_size", "mime_type", "upload_time", "source_system", "tag")
df_images.write.mode("append").insertInto("hive_prod.media_db.image_metadata")
```

**수정 B (테이블 생성):**
```python
# 추가된 코드
spark.sql("CREATE DATABASE IF NOT EXISTS hive_prod.media_db")

if not spark.catalog.tableExists("hive_prod.media_db.image_metadata"):
    spark.sql("""
    CREATE TABLE hive_prod.media_db.image_metadata (
        image_id STRING,
        s3_path STRING,
        file_size LONG,
        mime_type STRING,
        upload_time TIMESTAMP,
        source_system STRING,
        tag STRING
    )
    USING iceberg
    """)
    print("테이블 hive_prod.media_db.image_metadata 생성 완료")
```

---

## 4. DAG 코드 정리 (Import Error 방지)

### 증상 (Symptoms)
- 잠재적인 `ImportError` 가능성.

### 원인 (Cause)
- 사용하지 않는 `SQLExecuteQueryOperator`가 import 되어 있음.

### 조치 (Action)
- 불필요한 import 구문 삭제.

### 상세 수정 내역
**파일:** `dags/ml_pipeline_dag.py`

```python
# 수정 전
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ModuleNotFoundError:
    from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
import os

# 수정 후
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ModuleNotFoundError:
    from airflow.operators.python import PythonOperator
# from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator  <-- 삭제됨
import os
```

---

## 5. Visual Stack 헬스체크 실패

### 증상 (Symptoms)
- `node-exporter`, `superset-redis`, `opensearch-dashboards` 컨테이너 상태가 `healthy`로 표시되지 않음.
- `opensearch-dashboards`가 `unhealthy` 상태 (인증 실패).

### 원인 (Cause)
- `healthcheck` 설정이 누락되었거나, 보안 플러그인이 활성화된 OpenSearch에 인증 정보 없이 헬스체크를 시도함.

### 조치 (Action)
- 각 서비스에 맞는 `healthcheck` 명령어 추가.
- OpenSearch Dashboards에 인증 정보(`-u admin:...`) 및 환경 변수 추가.

### 상세 수정 내역
**파일:** `docker-compose-visual.yml`

**Superset Redis:**
```yaml
# 추가됨
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Node Exporter:**
```yaml
# 추가됨
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:9100/metrics"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**OpenSearch Dashboards:**
```yaml
# 수정 전
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5601/api/status"]

# 수정 후
    environment:
      OPENSEARCH_PASSWORD: ${OPENSEARCH_PASSWORD:-Admin@123} # 환경변수 추가
    healthcheck:
      test: ["CMD", "curl", "-f", "-u", "admin:${OPENSEARCH_PASSWORD:-Admin@123}", "http://localhost:5601/api/status"] # 인증 추가
```