# 🎯 End-to-End ML 파이프라인 모니터링 솔루션 가이드

**작성일**: 2025-12-25
**목적**: RAW → Bronze → Silver → Gold → Feature Engineering → 모델 학습 → 운영 전체 ML 파이프라인을 모니터링할 수 있는 엔터프라이즈 솔루션 비교

---

## 📋 목차

1. [솔루션 개요](#솔루션-개요)
2. [MLflow](#1-mlflow-추천-)
3. [Apache Airflow + MLflow](#2-apache-airflow--mlflow)
4. [Kubeflow](#3-kubeflow-kubernetes-기반)
5. [Prefect](#4-prefect-현대적-대안)
6. [DVC + CML](#5-dvc--cml)
7. [Feast](#6-feast-feature-store)
8. [솔루션 비교표](#-솔루션-비교표)
9. [현재 프로젝트 추천](#-현재-프로젝트-추천)
10. [통합 가이드](#-통합-가이드)

---

## 솔루션 개요

ML 파이프라인의 각 단계를 체계적으로 추적하고 모니터링하려면 전문 도구가 필요합니다.

### ML 파이프라인 단계

```
RAW Data (S3)
    ↓
Bronze Layer (Iceberg) - 원시 데이터 수집
    ↓
Silver Layer (Iceberg) - 데이터 정제/검증
    ↓
Gold Layer (Iceberg) - 집계/비즈니스 로직
    ↓
Feature Engineering - 피처 생성/선택
    ↓
Model Training - 모델 학습/하이퍼파라미터 튜닝
    ↓
Model Registry - 모델 버전 관리
    ↓
Production Deployment - 운영 배포
    ↓
Monitoring - 성능/드리프트 모니터링
```

---

## 1. MLflow (추천 ⭐)

**가장 인기 있는 오픈소스 ML 플랫폼**

### 핵심 기능

| 기능 | 설명 | 지원 여부 |
|------|------|----------|
| **Experiment Tracking** | 모델 파라미터, 메트릭, 아티팩트 추적 | ✅ |
| **Model Registry** | 모델 버전 관리 (Staging → Production) | ✅ |
| **Pipeline Tracking** | 데이터 처리 각 단계 로깅 | ✅ |
| **GUI Dashboard** | 전체 실험 비교, 모델 성능 시각화 | ✅ |
| **Auto Logging** | scikit-learn, PyTorch, TensorFlow 자동 로깅 | ✅ |

### 장점

- ✅ **가볍고 빠른 설치**: Docker 1개 컨테이너로 시작
- ✅ **광범위한 지원**: Apache Spark, scikit-learn, PyTorch, TensorFlow 모두 지원
- ✅ **쉬운 통합**: Python 코드 몇 줄 추가로 즉시 사용
- ✅ **S3 백엔드**: 현재 프로젝트의 SeaweedFS S3와 바로 통합 가능
- ✅ **무료 오픈소스**: Apache 2.0 라이선스

### 단점

- ⚠️ **워크플로우 오케스트레이션 약함**: 파이프라인 자동 실행 기능 제한적
- ⚠️ **스케줄링 없음**: Cron이나 이벤트 기반 실행 불가
- ⚠️ **복잡한 의존성 관리**: DAG 형태 파이프라인 정의 어려움

### 사용 예시

```python
import mlflow
import mlflow.spark
from pyspark.sql import SparkSession

# MLflow 서버 설정
mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("lakehouse-tick-pipeline")

# Bronze 단계
with mlflow.start_run(run_name="bronze_ingestion") as run:
    mlflow.log_param("source", "s3a://lakehouse/raw")
    mlflow.log_param("catalog", "hive_prod")

    # Spark 작업 실행
    df = spark.read.parquet("s3a://lakehouse/raw/ticks")
    row_count = df.count()

    mlflow.log_metric("rows_ingested", row_count)
    mlflow.log_metric("duration_seconds", 120)
    mlflow.set_tag("layer", "bronze")

# Silver 단계
with mlflow.start_run(run_name="silver_cleaning") as run:
    mlflow.log_param("bronze_table", "hive_prod.option_ticks_db.bronze_option_ticks")

    # 데이터 정제
    cleaned_df = df.dropna()
    cleaned_count = cleaned_df.count()

    mlflow.log_metric("rows_before", row_count)
    mlflow.log_metric("rows_after", cleaned_count)
    mlflow.log_metric("null_percentage", (1 - cleaned_count/row_count) * 100)
    mlflow.set_tag("layer", "silver")

# Gold 단계
with mlflow.start_run(run_name="gold_aggregation") as run:
    # 집계 작업
    agg_df = cleaned_df.groupBy("symbol").agg(...)

    mlflow.log_metric("final_rows", agg_df.count())
    mlflow.log_metric("unique_symbols", agg_df.select("symbol").distinct().count())
    mlflow.set_tag("layer", "gold")

# 모델 학습
with mlflow.start_run(run_name="model_training") as run:
    mlflow.log_param("algorithm", "RandomForest")
    mlflow.log_param("max_depth", 10)

    # 모델 학습
    model = train_model(...)

    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_metric("f1_score", 0.93)

    # 모델 저장
    mlflow.sklearn.log_model(model, "model")
    mlflow.register_model(f"runs:/{run.info.run_id}/model", "TickPricePredictor")
```

### Docker Compose 통합

```yaml
# docker-compose.yml에 추가
mlflow:
  image: ghcr.io/mlflow/mlflow:v2.9.2
  container_name: mlflow
  ports:
    - "5000:5000"
  environment:
    AWS_ACCESS_KEY_ID: seaweedfs_access_key
    AWS_SECRET_ACCESS_KEY: seaweedfs_secret_key
    AWS_ENDPOINT_URL_S3: http://seaweedfs-s3:8333
  command: >
    mlflow server
    --host 0.0.0.0
    --port 5000
    --backend-store-uri sqlite:///mlflow/mlflow.db
    --default-artifact-root s3://lakehouse/mlflow
  volumes:
    - mlflow-data:/mlflow
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3

volumes:
  mlflow-data:
```

### 접속 정보

- **URL**: http://localhost:5000
- **인증**: 없음 (기본 설정)
- **백엔드 스토어**: SQLite (개발용) / PostgreSQL (운영 권장)
- **아티팩트 스토어**: SeaweedFS S3

---

## 2. Apache Airflow + MLflow

**워크플로우 오케스트레이션 + ML 추적의 완벽한 조합**

### 핵심 기능

| 기능 | 설명 | 지원 여부 |
|------|------|----------|
| **DAG UI** | 각 단계 실행 상태 시각화 | ✅ |
| **Task Monitoring** | 실패/성공/재시도 추적 | ✅ |
| **Scheduling** | Cron 기반 자동 실행 | ✅ |
| **Dependency Management** | 복잡한 작업 의존성 관리 | ✅ |
| **Alerts** | Slack, Email, PagerDuty 알림 | ✅ |
| **MLflow 통합** | MLflow Tracking과 완벽 연동 | ✅ |

### 장점

- ✅ **업계 표준**: Netflix, Airbnb, Spotify, Uber 사용
- ✅ **복잡한 의존성 관리**: Bronze 완료 후 Silver 시작 등 조건부 실행
- ✅ **재시도 로직**: 실패 시 자동 재시도 및 백오프
- ✅ **풍부한 플러그인**: Spark, Trino, S3, Slack 등 300+ Operators
- ✅ **모니터링 대시보드**: 전체 파이프라인 상태 한눈에 확인

### 단점

- ⚠️ **복잡한 설치**: PostgreSQL, Redis 등 여러 컴포넌트 필요
- ⚠️ **러닝 커브**: DAG 작성에 Python 및 Airflow 지식 필요
- ⚠️ **리소스 사용**: 메모리 2GB+ 필요

### DAG 구조 예시

```python
# dags/ml_pipeline_dag.py
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import mlflow

default_args = {
    'owner': 'data-team',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'ml_pipeline',
    default_args=default_args,
    description='End-to-end ML Pipeline',
    schedule_interval='0 2 * * *',  # 매일 02:00 실행
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'lakehouse'],
) as dag:

    # Task 1: RAW → Bronze (Spark Job)
    raw_to_bronze = SparkSubmitOperator(
        task_id='raw_to_bronze',
        application='/opt/airflow/dags/scripts/bronze_ingestion.py',
        conn_id='spark_default',
        conf={
            'spark.sql.catalog.hive_prod': 'org.apache.iceberg.spark.SparkCatalog',
        },
    )

    # Task 2: Bronze → Silver (Data Cleaning)
    bronze_to_silver = SparkSubmitOperator(
        task_id='bronze_to_silver',
        application='/opt/airflow/dags/scripts/silver_cleaning.py',
        conn_id='spark_default',
    )

    # Task 3: Silver → Gold (Aggregation)
    silver_to_gold = SparkSubmitOperator(
        task_id='silver_to_gold',
        application='/opt/airflow/dags/scripts/gold_aggregation.py',
        conn_id='spark_default',
    )

    # Task 4: Feature Engineering
    def feature_engineering(**context):
        mlflow.set_tracking_uri("http://mlflow:5000")
        with mlflow.start_run(run_name="feature_engineering"):
            # Feature 생성 로직
            mlflow.log_metric("features_created", 25)
            return "success"

    feature_task = PythonOperator(
        task_id='feature_engineering',
        python_callable=feature_engineering,
    )

    # Task 5: Model Training (MLflow 연동)
    def train_model(**context):
        mlflow.set_tracking_uri("http://mlflow:5000")
        with mlflow.start_run(run_name="model_training"):
            mlflow.log_param("algorithm", "XGBoost")
            # 모델 학습
            mlflow.log_metric("accuracy", 0.95)
            return "model_trained"

    train_task = PythonOperator(
        task_id='model_training',
        python_callable=train_model,
    )

    # Task 6: Model Deployment
    def deploy_model(**context):
        # 모델 배포 로직
        return "deployed"

    deploy_task = PythonOperator(
        task_id='model_deployment',
        python_callable=deploy_model,
    )

    # 의존성 정의
    raw_to_bronze >> bronze_to_silver >> silver_to_gold >> feature_task >> train_task >> deploy_task
```

### Docker Compose 통합

```yaml
# Airflow + MLflow 전체 스택
airflow-postgres:
  image: postgres:15
  container_name: airflow-postgres
  environment:
    POSTGRES_USER: airflow
    POSTGRES_PASSWORD: airflow
    POSTGRES_DB: airflow
  volumes:
    - airflow-postgres-data:/var/lib/postgresql/data
  networks:
    - lakehouse-net

airflow-redis:
  image: redis:7-alpine
  container_name: airflow-redis
  networks:
    - lakehouse-net

airflow-webserver:
  image: apache/airflow:2.8.0-python3.11
  container_name: airflow-webserver
  depends_on:
    - airflow-postgres
    - airflow-redis
  environment:
    AIRFLOW__CORE__EXECUTOR: CeleryExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow
    AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://airflow:airflow@airflow-postgres/airflow
    AIRFLOW__CELERY__BROKER_URL: redis://airflow-redis:6379/0
    AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
  ports:
    - "8080:8080"
  volumes:
    - ./dags:/opt/airflow/dags
    - ./logs:/opt/airflow/logs
    - ./plugins:/opt/airflow/plugins
  networks:
    - lakehouse-net
  command: webserver

airflow-scheduler:
  image: apache/airflow:2.8.0-python3.11
  container_name: airflow-scheduler
  depends_on:
    - airflow-postgres
    - airflow-redis
  environment:
    AIRFLOW__CORE__EXECUTOR: CeleryExecutor
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow
    AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://airflow:airflow@airflow-postgres/airflow
    AIRFLOW__CELERY__BROKER_URL: redis://airflow-redis:6379/0
  volumes:
    - ./dags:/opt/airflow/dags
    - ./logs:/opt/airflow/logs
    - ./plugins:/opt/airflow/plugins
  networks:
    - lakehouse-net
  command: scheduler

volumes:
  airflow-postgres-data:
```

### 접속 정보

- **URL**: http://localhost:8080
- **기본 계정**: admin / admin
- **MLflow 연동**: http://mlflow:5000 (내부 네트워크)

---

## 3. Kubeflow (Kubernetes 기반)

**전체 ML 워크플로우 관리 플랫폼**

### 핵심 기능

| 기능 | 설명 | 지원 여부 |
|------|------|----------|
| **Pipelines** | DAG 형태 파이프라인 시각화 | ✅ |
| **Experiments** | 하이퍼파라미터 튜닝 추적 | ✅ |
| **Notebooks** | Jupyter 통합 | ✅ |
| **Model Serving** | TensorFlow Serving, KFServing | ✅ |
| **Auto Scaling** | Kubernetes 네이티브 스케일링 | ✅ |
| **Multi-Tenancy** | 팀별 네임스페이스 격리 | ✅ |

### 장점

- ✅ **Google 지원**: TFX(TensorFlow Extended) 통합
- ✅ **Kubernetes 네이티브**: 자동 스케일링 및 리소스 관리
- ✅ **전체 MLOps 스택**: 파이프라인 + 실험 + 서빙 모두 포함
- ✅ **엔터프라이즈급**: 대규모 ML 팀에 적합

### 단점

- ❌ **복잡한 설치**: Kubernetes 클러스터 필수
- ❌ **오버킬**: 작은 프로젝트에는 너무 복잡
- ❌ **높은 러닝 커브**: Kubernetes, Kubeflow SDK 모두 학습 필요
- ❌ **리소스 집약적**: 최소 8GB 메모리 필요

### 권장 사용 사례

- 대규모 ML 팀 (10명 이상)
- Kubernetes 인프라 이미 보유
- 복잡한 분산 학습 필요
- 엔터프라이즈 MLOps 구축

### 현재 프로젝트 적합도

⚠️ **권장하지 않음** - 현재 Docker Compose 기반 환경에 오버킬

---

## 4. Prefect (현대적 대안)

**Python 네이티브 워크플로우 엔진**

### 핵심 기능

| 기능 | 설명 | 지원 여부 |
|------|------|----------|
| **Flow UI** | 실시간 파이프라인 진행률 | ✅ |
| **Task States** | 각 단계 성공/실패/스킵 상태 | ✅ |
| **Retry Logic** | 자동 재시도 설정 | ✅ |
| **Cloud/Self-hosted** | 클라우드 또는 셀프 호스팅 | ✅ |
| **Python Decorators** | 기존 함수에 @task 추가만으로 사용 | ✅ |

### 장점

- ✅ **Airflow보다 간단**: Python 데코레이터만 추가
- ✅ **아름다운 UI**: 현대적이고 직관적인 대시보드
- ✅ **빠른 개발**: 기존 코드 수정 최소화
- ✅ **유연한 배포**: Cloud 또는 Self-hosted 선택 가능

### 단점

- ⚠️ **생태계 작음**: Airflow보다 플러그인 적음
- ⚠️ **비교적 신생**: Airflow 대비 검증 부족
- ⚠️ **클라우드 의존**: 무료 버전은 기능 제한적

### 사용 예시

```python
from prefect import flow, task
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
import mlflow

@task(retries=3, retry_delay_seconds=60)
def raw_to_bronze():
    """RAW 데이터를 Bronze Layer로 이동"""
    mlflow.set_tracking_uri("http://mlflow:5000")
    with mlflow.start_run(run_name="bronze_ingestion"):
        # Spark 작업
        row_count = 10000
        mlflow.log_metric("rows_ingested", row_count)
        return row_count

@task(retries=3)
def bronze_to_silver(bronze_count: int):
    """Bronze 데이터를 정제하여 Silver Layer로"""
    with mlflow.start_run(run_name="silver_cleaning"):
        cleaned_count = int(bronze_count * 0.95)
        mlflow.log_metric("rows_cleaned", cleaned_count)
        return cleaned_count

@task(retries=3)
def silver_to_gold(silver_count: int):
    """Silver 데이터를 집계하여 Gold Layer로"""
    with mlflow.start_run(run_name="gold_aggregation"):
        agg_count = int(silver_count * 0.9)
        mlflow.log_metric("final_rows", agg_count)
        return agg_count

@task
def train_model(gold_count: int):
    """모델 학습"""
    with mlflow.start_run(run_name="model_training"):
        mlflow.log_param("data_size", gold_count)
        mlflow.log_metric("accuracy", 0.95)
        return "model_v1"

@flow(name="ml-pipeline", log_prints=True)
def ml_pipeline():
    """전체 ML 파이프라인"""
    bronze_count = raw_to_bronze()
    silver_count = bronze_to_silver(bronze_count)
    gold_count = silver_to_gold(silver_count)
    model = train_model(gold_count)
    print(f"Pipeline completed! Model: {model}")

# 스케줄 설정 (매일 02:00 실행)
deployment = Deployment.build_from_flow(
    flow=ml_pipeline,
    name="daily-ml-pipeline",
    schedule=CronSchedule(cron="0 2 * * *"),
)

if __name__ == "__main__":
    deployment.apply()
```

### Docker Compose 통합

```yaml
prefect-server:
  image: prefecthq/prefect:2.14-python3.11
  container_name: prefect-server
  ports:
    - "4200:4200"
  environment:
    PREFECT_SERVER_API_HOST: 0.0.0.0
    PREFECT_API_DATABASE_CONNECTION_URL: postgresql+asyncpg://prefect:prefect@prefect-postgres:5432/prefect
  command: prefect server start
  depends_on:
    - prefect-postgres
  networks:
    - lakehouse-net

prefect-postgres:
  image: postgres:15
  container_name: prefect-postgres
  environment:
    POSTGRES_USER: prefect
    POSTGRES_PASSWORD: prefect
    POSTGRES_DB: prefect
  volumes:
    - prefect-data:/var/lib/postgresql/data
  networks:
    - lakehouse-net

volumes:
  prefect-data:
```

### 접속 정보

- **URL**: http://localhost:4200
- **인증**: 없음 (Self-hosted 버전)
- **MLflow 연동**: Python 코드에서 직접 호출

---

## 5. DVC + CML

**Git 스타일 데이터/모델 버전 관리**

### 핵심 기능

| 기능 | 설명 | 지원 여부 |
|------|------|----------|
| **Data Versioning** | Bronze/Silver/Gold 데이터셋 버전 추적 | ✅ |
| **Model Versioning** | 학습된 모델 버전 관리 | ✅ |
| **Pipeline as Code** | YAML로 파이프라인 정의 | ✅ |
| **CML (CI/CD)** | GitHub Actions에서 모델 메트릭 자동 리포트 | ✅ |
| **Experiments** | Git 브랜치처럼 실험 관리 | ✅ |

### 장점

- ✅ **Git 워크플로우**: Git 사용자에게 친숙
- ✅ **S3 백엔드**: SeaweedFS S3와 완벽 통합
- ✅ **가벼움**: Python 패키지 설치만으로 사용
- ✅ **CI/CD 통합**: GitHub Actions, GitLab CI와 연동

### 단점

- ⚠️ **실시간 모니터링 약함**: GUI 대시보드 없음
- ⚠️ **오케스트레이션 부족**: 자동 실행 기능 제한적
- ⚠️ **러닝 커브**: DVC CLI 및 개념 학습 필요

### dvc.yaml 예시

```yaml
# dvc.yaml - 파이프라인 정의
stages:
  raw_to_bronze:
    cmd: python scripts/bronze_ingestion.py
    deps:
      - scripts/bronze_ingestion.py
      - s3://lakehouse/raw/ticks
    params:
      - config.yaml:
          - bronze.batch_size
          - bronze.partition_cols
    outs:
      - s3://lakehouse/bronze/option_ticks:
          cache: false
    metrics:
      - metrics/bronze.json:
          cache: false

  bronze_to_silver:
    cmd: python scripts/silver_cleaning.py
    deps:
      - scripts/silver_cleaning.py
      - s3://lakehouse/bronze/option_ticks
    params:
      - config.yaml:
          - silver.null_threshold
          - silver.validation_rules
    outs:
      - s3://lakehouse/silver/option_ticks:
          cache: false
    metrics:
      - metrics/silver.json:
          cache: false

  silver_to_gold:
    cmd: python scripts/gold_aggregation.py
    deps:
      - scripts/gold_aggregation.py
      - s3://lakehouse/silver/option_ticks
    outs:
      - s3://lakehouse/gold/option_ticks:
          cache: false
    metrics:
      - metrics/gold.json:
          cache: false

  feature_engineering:
    cmd: python scripts/features.py
    deps:
      - scripts/features.py
      - s3://lakehouse/gold/option_ticks
    outs:
      - features/train.parquet
      - features/test.parquet
    metrics:
      - metrics/features.json

  train_model:
    cmd: python scripts/train.py
    deps:
      - scripts/train.py
      - features/train.parquet
      - features/test.parquet
    params:
      - config.yaml:
          - model.algorithm
          - model.max_depth
          - model.learning_rate
    outs:
      - models/model.pkl
    metrics:
      - metrics/train.json:
          cache: false
    plots:
      - plots/confusion_matrix.png
      - plots/roc_curve.png
```

### 실행 방법

```bash
# 전체 파이프라인 실행
dvc repro

# 특정 단계만 실행
dvc repro silver_to_gold

# 실험 비교
dvc exp show

# 메트릭 비교
dvc metrics diff
```

---

## 6. Feast (Feature Store)

**Feature Engineering 전용 솔루션**

### 핵심 기능

| 기능 | 설명 | 지원 여부 |
|------|------|----------|
| **Feature Registry** | Feature 메타데이터 중앙 관리 | ✅ |
| **Point-in-time Correctness** | 학습/서빙 데이터 일관성 보장 | ✅ |
| **Online/Offline Store** | Redis (온라인) + S3 (오프라인) | ✅ |
| **Feature Reuse** | 팀 간 Feature 공유 | ✅ |

### 장점

- ✅ **Feature 재사용**: 한 번 정의한 Feature를 여러 모델에서 사용
- ✅ **학습/운영 일치**: Point-in-time Join으로 데이터 누수 방지
- ✅ **빠른 서빙**: Redis에서 밀리초 단위 Feature 조회

### 단점

- ❌ **파이프라인 모니터링 없음**: Feature Store 기능만 제공
- ❌ **제한적 범위**: Feature Engineering 단계에만 사용

### 현재 프로젝트 적합도

⚠️ **추가 도구로 고려** - MLflow/Airflow와 함께 사용

---

## 📊 솔루션 비교표

| 솔루션 | 설치 난이도 | 파이프라인 모니터링 | 모델 추적 | 운영 배포 | 비용 | 추천도 |
|--------|------------|-------------------|----------|----------|------|--------|
| **MLflow** | ⭐ 쉬움 | ⚠️ 제한적 | ✅ 최고 | ✅ 가능 | 무료 | ⭐⭐⭐⭐⭐ |
| **Airflow + MLflow** | ⭐⭐⭐ 중간 | ✅ 최고 | ✅ 최고 | ✅ 가능 | 무료 | ⭐⭐⭐⭐⭐ |
| **Kubeflow** | ⭐⭐⭐⭐⭐ 어려움 | ✅ 우수 | ✅ 우수 | ✅ 최고 | 무료 | ⭐⭐⭐ |
| **Prefect** | ⭐⭐ 쉬움 | ✅ 최고 | ⚠️ 제한적 | ✅ 가능 | 무료/유료 | ⭐⭐⭐⭐ |
| **DVC + CML** | ⭐⭐ 쉬움 | ✅ 우수 | ✅ 우수 | ⚠️ 제한적 | 무료 | ⭐⭐⭐⭐ |
| **Feast** | ⭐⭐⭐ 중간 | ❌ 없음 | ❌ 없음 | ✅ Feature만 | 무료 | ⭐⭐⭐ |

### 세부 비교

#### 설치 시간

| 솔루션 | 초기 설치 | 통합 시간 | 총 소요 시간 |
|--------|----------|----------|-------------|
| MLflow | 10분 | 2시간 | **1일** |
| Airflow + MLflow | 1시간 | 1주 | **1주** |
| Kubeflow | 1일 | 2주 | **3주** |
| Prefect | 15분 | 3시간 | **3일** |
| DVC + CML | 5분 | 1일 | **2일** |

#### 리소스 요구사항

| 솔루션 | 메모리 | CPU | 디스크 | 컨테이너 수 |
|--------|--------|-----|--------|------------|
| MLflow | 512MB | 0.5 | 10GB | 1개 |
| Airflow | 2GB | 1.0 | 20GB | 4개 |
| Kubeflow | 8GB | 4.0 | 100GB | 10개+ |
| Prefect | 1GB | 0.5 | 15GB | 2개 |
| DVC | 100MB | 0.1 | 5GB | 0개 (CLI) |

---

## 🎯 현재 프로젝트 추천

### 옵션 1: MLflow 단독 (⭐ 가장 빠름 - 1일)

**추천 대상**: 빠른 프로토타입, 모델 학습 추적만 필요한 경우

**장점**:
- ✅ Docker 컨테이너 1개 추가만으로 즉시 사용
- ✅ Spark 코드에 `mlflow.log_*()` 몇 줄만 추가
- ✅ 현재 SeaweedFS S3와 완벽 통합

**단점**:
- ⚠️ 파이프라인 자동 실행 불가 (수동으로 fspark.py 실행)
- ⚠️ 스케줄링 기능 없음

**구현 계획**:
1. docker-compose.yml에 mlflow 서비스 추가
2. fspark.py에 MLflow 로깅 코드 추가
3. http://localhost:5000 접속하여 실험 확인

---

### 옵션 2: Airflow + MLflow (⭐⭐ 완벽한 솔루션 - 1주)

**추천 대상**: 엔터프라이즈급 MLOps, 자동화된 파이프라인 필요

**장점**:
- ✅ 전체 파이프라인 자동화 + 모델 추적
- ✅ 업계 표준 조합
- ✅ 복잡한 의존성 관리 가능
- ✅ Cron 기반 자동 실행

**단점**:
- ⚠️ 초기 설정 시간 필요 (1주)
- ⚠️ 리소스 사용량 증가 (메모리 2GB+)

**구현 계획**:
1. docker-compose.yml에 Airflow 스택 추가 (PostgreSQL, Redis, Webserver, Scheduler)
2. fspark.py를 Airflow DAG로 변환
3. MLflow 연동 설정
4. 스케줄 설정 및 테스트

---

### 옵션 3: Prefect + MLflow (⭐⭐ 현대적 - 3일)

**추천 대상**: Airflow보다 간단하고 빠른 개발 원하는 경우

**장점**:
- ✅ Airflow보다 설정 간단
- ✅ Python 데코레이터 방식으로 쉬운 통합
- ✅ 아름다운 UI

**단점**:
- ⚠️ Airflow 대비 생태계 작음
- ⚠️ 클라우드 버전은 유료

**구현 계획**:
1. docker-compose.yml에 Prefect 서버 추가
2. fspark.py에 @flow, @task 데코레이터 추가
3. Prefect UI에서 스케줄 설정

---

## 🚀 통합 가이드

### Step 1: MLflow 빠른 시작 (30분)

#### 1.1 Docker Compose 수정

```bash
cd /home/i/work/ai/lakehouse-tick
```

docker-compose.yml에 추가:

```yaml
mlflow:
  image: ghcr.io/mlflow/mlflow:v2.9.2
  container_name: mlflow
  ports:
    - "5000:5000"
  environment:
    AWS_ACCESS_KEY_ID: seaweedfs_access_key
    AWS_SECRET_ACCESS_KEY: seaweedfs_secret_key
    MLFLOW_S3_ENDPOINT_URL: http://seaweedfs-s3:8333
  command: >
    mlflow server
    --host 0.0.0.0
    --port 5000
    --backend-store-uri sqlite:///mlflow/mlflow.db
    --default-artifact-root s3://lakehouse/mlflow
  volumes:
    - mlflow-data:/mlflow
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3

volumes:
  mlflow-data:
```

#### 1.2 서비스 시작

```bash
docker compose up -d mlflow
docker compose ps mlflow
```

#### 1.3 fspark.py에 MLflow 추가

```python
# python/fspark.py 상단에 추가
import mlflow

# MLflow 설정
mlflow.set_tracking_uri("http://localhost:5000")  # 로컬 개발
# mlflow.set_tracking_uri("http://mlflow:5000")  # Docker 내부
mlflow.set_experiment("lakehouse-tick-pipeline")

# 기존 코드 수정 예시
with mlflow.start_run(run_name="bronze_ingestion"):
    mlflow.log_param("catalog", "hive_prod")
    mlflow.log_param("warehouse", "s3a://lakehouse/warehouse")

    # 기존 Spark 작업 실행
    # ...

    mlflow.log_metric("rows_processed", row_count)
    mlflow.log_metric("duration_seconds", duration)
```

#### 1.4 접속 확인

```bash
# 브라우저에서 접속
http://localhost:5000
```

---

### Step 2: Airflow 통합 (1주)

#### 2.1 디렉토리 구조 생성

```bash
mkdir -p dags/scripts
mkdir -p logs
mkdir -p plugins
```

#### 2.2 DAG 파일 작성

`dags/ml_pipeline_dag.py` 생성 (위 Airflow 섹션 참고)

#### 2.3 Docker Compose에 Airflow 추가

위 Airflow 섹션의 docker-compose.yml 참고

#### 2.4 초기화 및 시작

```bash
# DB 초기화
docker compose run airflow-webserver airflow db init

# Admin 사용자 생성
docker compose run airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# 서비스 시작
docker compose up -d airflow-webserver airflow-scheduler

# 접속 확인
http://localhost:8080
```

---

## ✅ 체크리스트

### MLflow 단독 구현

- [ ] docker-compose.yml에 mlflow 서비스 추가
- [ ] mlflow-data 볼륨 생성
- [ ] `docker compose up -d mlflow` 실행
- [ ] http://localhost:5000 접속 확인
- [ ] fspark.py에 MLflow import 추가
- [ ] 실험 추적 코드 작성
- [ ] 첫 실험 실행 및 UI 확인

### Airflow + MLflow 구현

- [ ] Airflow 디렉토리 구조 생성
- [ ] docker-compose.yml에 Airflow 스택 추가
- [ ] DB 초기화 및 admin 사용자 생성
- [ ] DAG 파일 작성
- [ ] Airflow UI 접속 확인
- [ ] fspark.py를 SparkSubmitOperator로 변환
- [ ] MLflow 연동 테스트
- [ ] 스케줄 설정 및 자동 실행 확인

---

## 📚 참고 자료

### 공식 문서

- **MLflow**: https://mlflow.org/docs/latest/
- **Apache Airflow**: https://airflow.apache.org/docs/
- **Kubeflow**: https://www.kubeflow.org/docs/
- **Prefect**: https://docs.prefect.io/
- **DVC**: https://dvc.org/doc
- **Feast**: https://docs.feast.dev/

### 튜토리얼

- [MLflow with Spark](https://mlflow.org/docs/latest/tracking.html#apache-spark)
- [Airflow DAG Tutorial](https://airflow.apache.org/docs/apache-airflow/stable/tutorial.html)
- [Prefect Quickstart](https://docs.prefect.io/latest/getting-started/quickstart/)

---

## 🎉 결론

**현재 프로젝트에 가장 적합한 솔루션**:

### 🥇 1순위: MLflow 단독 (빠른 시작)
- **시간**: 1일
- **난이도**: ⭐ 쉬움
- **추천**: 프로토타입, 모델 추적만 필요

### 🥈 2순위: Airflow + MLflow (완벽)
- **시간**: 1주
- **난이도**: ⭐⭐⭐ 중간
- **추천**: 엔터프라이즈급 MLOps 구축

### 🥉 3순위: Prefect + MLflow (현대적)
- **시간**: 3일
- **난이도**: ⭐⭐ 쉬움
- **추천**: 빠른 개발 + 아름다운 UI

---

**작성**: 2025-12-25
**버전**: 1.0
**다음 문서**: [DEVELOPMENT_CHECKLIST.md](DEVELOPMENT_CHECKLIST.md)

---

## 🔧 옵션 2: 별도 docker-compose-mlops.yml 구현 가이드

**선택 이유**: MLOps 서비스를 기존 Lakehouse 인프라와 분리하여 독립적으로 관리하고 싶을 때

### 📋 개요

이 가이드는 Airflow + MLflow 스택을 **별도의 docker-compose-mlops.yml 파일**로 분리하여 구현하는 방법을 다룹니다.

#### 장점
- ✅ **독립적 생명주기**: MLOps 스택만 별도로 시작/중지 가능
- ✅ **파일 관리 명확**: 각 파일의 책임이 명확히 분리됨
- ✅ **개발/운영 분리**: 데이터 인프라와 ML 워크플로우 독립 관리
- ✅ **롤백 용이**: MLOps 스택에 문제 발생 시 쉽게 제거 가능

#### 단점
- ⚠️ **두 번의 명령어**: 두 개의 docker-compose 파일 별도 실행 필요
- ⚠️ **네트워크 설정**: External network 설정 필수
- ⚠️ **환경 변수 중복**: 일부 환경 변수를 두 파일에서 관리

---

### 1️⃣ 디렉토리 구조

```bash
/home/i/work/ai/lakehouse-tick/
├── docker-compose.yml              # 기존 Lakehouse 인프라 (19개 서비스)
├── docker-compose-mlops.yml        # 신규 MLOps 스택 (5개 서비스)
├── .env                            # 공통 환경 변수
├── .env.mlops                      # MLOps 전용 환경 변수 (선택)
├── dags/                           # Airflow DAG 파일
│   ├── ml_pipeline_dag.py
│   └── scripts/
│       ├── bronze_ingestion.py
│       ├── silver_cleaning.py
│       └── gold_aggregation.py
├── logs/                           # 로그 디렉토리
│   ├── airflow/
│   └── mlflow/
└── plugins/                        # Airflow 플러그인 (선택)
```

---

### 2️⃣ docker-compose-mlops.yml 전체 코드

#### 2.1 파일 생성

```bash
cd /home/i/work/ai/lakehouse-tick
touch docker-compose-mlops.yml
```

#### 2.2 전체 YAML 내용

```yaml
# ============================================================================
# MLOps Stack - Separate Compose File
# ============================================================================
#
# 이 파일은 기존 docker-compose.yml과 독립적으로 실행됩니다.
#
# 실행 방법:
#   docker compose -f docker-compose-mlops.yml up -d
#
# 중지 방법:
#   docker compose -f docker-compose-mlops.yml down
#
# 기존 Lakehouse 인프라와 통신하기 위해 external network 사용
# ============================================================================

version: '3.8'

services:
  # ============================================================================
  # MLflow - Experiment Tracking & Model Registry
  # ============================================================================
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.9.2
    container_name: mlflow
    ports:
      - "5000:5000"
    environment:
      # S3 Backend (SeaweedFS)
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-seaweedfs_access_key}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-seaweedfs_secret_key}
      MLFLOW_S3_ENDPOINT_URL: http://seaweedfs-s3:8333

      # MLflow 설정
      MLFLOW_BACKEND_STORE_URI: sqlite:///mlflow/mlflow.db
      MLFLOW_DEFAULT_ARTIFACT_ROOT: s3://lakehouse/mlflow
    command: >
      mlflow server
      --host 0.0.0.0
      --port 5000
      --backend-store-uri sqlite:///mlflow/mlflow.db
      --default-artifact-root s3://lakehouse/mlflow
    volumes:
      - mlflow-data:/mlflow
      - ./logs/mlflow:/mlflow/logs
    networks:
      - lakehouse-net  # External network (기존 docker-compose.yml에서 생성)
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  # ============================================================================
  # Airflow PostgreSQL - Airflow 메타스토어
  # ============================================================================
  airflow-postgres:
    image: postgres:15-alpine
    container_name: airflow-postgres
    environment:
      POSTGRES_USER: ${AIRFLOW_POSTGRES_USER:-airflow}
      POSTGRES_PASSWORD: ${AIRFLOW_POSTGRES_PASSWORD:-airflow}
      POSTGRES_DB: ${AIRFLOW_POSTGRES_DB:-airflow}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - airflow-postgres-data:/var/lib/postgresql/data
    networks:
      - lakehouse-net
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow", "-d", "airflow"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  # ============================================================================
  # Airflow Redis - Celery 브로커
  # ============================================================================
  airflow-redis:
    image: redis:7-alpine
    container_name: airflow-redis
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - airflow-redis-data:/data
    networks:
      - lakehouse-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  # ============================================================================
  # Airflow Webserver - UI & API
  # ============================================================================
  airflow-webserver:
    image: apache/airflow:2.8.0-python3.11
    container_name: airflow-webserver
    depends_on:
      airflow-postgres:
        condition: service_healthy
      airflow-redis:
        condition: service_healthy
    ports:
      - "8080:8080"
    environment:
      # Core
      AIRFLOW__CORE__EXECUTOR: CeleryExecutor
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY:-46BKJoQYlPPOexq0OhDZnIlNepKFf87WFwLbfzqDDho=}
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
      AIRFLOW__CORE__DEFAULT_TIMEZONE: Asia/Seoul

      # Database
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow

      # Celery
      AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://airflow:airflow@airflow-postgres/airflow
      AIRFLOW__CELERY__BROKER_URL: redis://airflow-redis:6379/0

      # Webserver
      AIRFLOW__WEBSERVER__SECRET_KEY: ${AIRFLOW_WEBSERVER_SECRET_KEY:-airflow-secret-key}
      AIRFLOW__WEBSERVER__EXPOSE_CONFIG: 'true'

      # Logging
      AIRFLOW__LOGGING__BASE_LOG_FOLDER: /opt/airflow/logs
      AIRFLOW__LOGGING__LOGGING_LEVEL: INFO

      # Scheduler
      AIRFLOW__SCHEDULER__ENABLE_HEALTH_CHECK: 'true'

      # S3 연동 (SeaweedFS)
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-seaweedfs_access_key}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-seaweedfs_secret_key}
      AWS_ENDPOINT_URL_S3: http://seaweedfs-s3:8333

      # MLflow 연동
      MLFLOW_TRACKING_URI: http://mlflow:5000
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs/airflow:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    networks:
      - lakehouse-net
    command: webserver
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  # ============================================================================
  # Airflow Scheduler - DAG 스케줄링
  # ============================================================================
  airflow-scheduler:
    image: apache/airflow:2.8.0-python3.11
    container_name: airflow-scheduler
    depends_on:
      airflow-postgres:
        condition: service_healthy
      airflow-redis:
        condition: service_healthy
    environment:
      # Core
      AIRFLOW__CORE__EXECUTOR: CeleryExecutor
      AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY:-46BKJoQYlPPOexq0OhDZnIlNepKFf87WFwLbfzqDDho=}
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
      AIRFLOW__CORE__DEFAULT_TIMEZONE: Asia/Seoul

      # Database
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@airflow-postgres/airflow

      # Celery
      AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://airflow:airflow@airflow-postgres/airflow
      AIRFLOW__CELERY__BROKER_URL: redis://airflow-redis:6379/0

      # Logging
      AIRFLOW__LOGGING__BASE_LOG_FOLDER: /opt/airflow/logs
      AIRFLOW__LOGGING__LOGGING_LEVEL: INFO

      # Scheduler
      AIRFLOW__SCHEDULER__ENABLE_HEALTH_CHECK: 'true'
      AIRFLOW__SCHEDULER__CATCHUP_BY_DEFAULT: 'false'

      # S3 연동 (SeaweedFS)
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-seaweedfs_access_key}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-seaweedfs_secret_key}
      AWS_ENDPOINT_URL_S3: http://seaweedfs-s3:8333

      # MLflow 연동
      MLFLOW_TRACKING_URI: http://mlflow:5000
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs/airflow:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    networks:
      - lakehouse-net
    command: scheduler
    healthcheck:
      test: ["CMD", "airflow", "jobs", "check", "--job-type", "SchedulerJob", "--hostname", "$HOSTNAME"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

# ============================================================================
# Networks - External Network 사용
# ============================================================================
networks:
  lakehouse-net:
    external: true  # 기존 docker-compose.yml에서 생성된 네트워크 사용

# ============================================================================
# Volumes - MLOps 전용 볼륨
# ============================================================================
volumes:
  mlflow-data:
    driver: local
  airflow-postgres-data:
    driver: local
  airflow-redis-data:
    driver: local
```

---

### 3️⃣ External Network 설정

#### 3.1 기존 docker-compose.yml 수정

기존 `docker-compose.yml`에서 **네트워크를 external로 변경**해야 합니다.

**변경 전**:
```yaml
networks:
  default:
    name: lakehouse-net
```

**변경 후**:
```yaml
networks:
  lakehouse-net:
    driver: bridge
    name: lakehouse-net
```

#### 3.2 네트워크 생성 확인

```bash
# 기존 네트워크가 없다면 수동 생성
docker network create lakehouse-net

# 네트워크 확인
docker network ls | grep lakehouse-net
```

---

### 4️⃣ 환경 변수 관리

#### 4.1 .env 파일 확장

기존 `.env` 파일에 MLOps 관련 환경 변수 추가:

```bash
# ============================================================================
# 기존 환경 변수 (유지)
# ============================================================================
AWS_ACCESS_KEY_ID=seaweedfs_access_key
AWS_SECRET_ACCESS_KEY=seaweedfs_secret_key
AWS_REGION=us-east-1

# ============================================================================
# MLOps 환경 변수 (추가)
# ============================================================================

# Airflow PostgreSQL
AIRFLOW_POSTGRES_USER=airflow
AIRFLOW_POSTGRES_PASSWORD=airflow
AIRFLOW_POSTGRES_DB=airflow

# Airflow Security Keys
# Fernet Key 생성: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
AIRFLOW_FERNET_KEY=46BKJoQYlPPOexq0OhDZnIlNepKFf87WFwLbfzqDDho=

# Webserver Secret Key
AIRFLOW_WEBSERVER_SECRET_KEY=airflow-secret-key-change-this

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000
```

#### 4.2 .env.mlops 파일 (선택사항)

MLOps 전용 환경 변수를 별도로 관리하고 싶다면:

```bash
# .env.mlops
AIRFLOW_POSTGRES_USER=airflow
AIRFLOW_POSTGRES_PASSWORD=airflow
AIRFLOW_POSTGRES_DB=airflow
AIRFLOW_FERNET_KEY=46BKJoQYlPPOexq0OhDZnIlNepKFf87WFwLbfzqDDho=
AIRFLOW_WEBSERVER_SECRET_KEY=airflow-secret-key
```

실행 시:
```bash
docker compose -f docker-compose-mlops.yml --env-file .env.mlops up -d
```

---

### 5️⃣ 디렉토리 생성

```bash
cd /home/i/work/ai/lakehouse-tick

# DAG 디렉토리
mkdir -p dags/scripts

# 로그 디렉토리
mkdir -p logs/airflow
mkdir -p logs/mlflow

# 플러그인 디렉토리 (선택)
mkdir -p plugins

# 권한 설정 (Airflow는 UID 50000 사용)
sudo chown -R 50000:50000 dags logs plugins
```

---

### 6️⃣ 실행 가이드

#### 6.1 전체 스택 시작 (순서 중요)

```bash
cd /home/i/work/ai/lakehouse-tick

# 1단계: 기존 Lakehouse 인프라 시작
docker compose up -d

# 2단계: 네트워크 존재 확인
docker network ls | grep lakehouse-net

# 3단계: MLOps 스택 시작
docker compose -f docker-compose-mlops.yml up -d

# 4단계: 전체 서비스 상태 확인
docker compose ps
docker compose -f docker-compose-mlops.yml ps
```

#### 6.2 Airflow 초기화 (최초 1회만)

```bash
# DB 마이그레이션
docker compose -f docker-compose-mlops.yml run --rm airflow-webserver airflow db migrate

# Admin 사용자 생성
docker compose -f docker-compose-mlops.yml run --rm airflow-webserver \
  airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# 초기화 완료 확인
docker compose -f docker-compose-mlops.yml logs airflow-webserver | grep "Webserver started"
```

#### 6.3 접속 확인

```bash
# MLflow UI
curl -f http://localhost:5000/health && echo "✅ MLflow OK"

# Airflow UI
curl -f http://localhost:8080/health && echo "✅ Airflow OK"

# 브라우저 접속
# MLflow: http://localhost:5000
# Airflow: http://localhost:8080 (admin/admin)
```

---

### 7️⃣ DAG 파일 작성

#### 7.1 샘플 DAG 생성

`dags/ml_pipeline_dag.py`:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import mlflow

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'ml_pipeline',
    default_args=default_args,
    description='End-to-end ML Pipeline with MLflow',
    schedule_interval='0 2 * * *',  # 매일 02:00
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'lakehouse', 'mlflow'],
) as dag:

    def log_to_mlflow(**context):
        """MLflow에 메트릭 로깅"""
        mlflow.set_tracking_uri("http://mlflow:5000")
        mlflow.set_experiment("lakehouse-tick-pipeline")

        with mlflow.start_run(run_name=context['task_instance'].task_id):
            mlflow.log_param("dag_id", context['dag'].dag_id)
            mlflow.log_param("execution_date", str(context['execution_date']))
            mlflow.log_metric("test_metric", 100)
            print(f"✅ Logged to MLflow: {context['task_instance'].task_id}")

    # Task 1: Bronze Layer 처리
    bronze_task = PythonOperator(
        task_id='bronze_ingestion',
        python_callable=log_to_mlflow,
    )

    # Task 2: Silver Layer 처리
    silver_task = PythonOperator(
        task_id='silver_cleaning',
        python_callable=log_to_mlflow,
    )

    # Task 3: Gold Layer 처리
    gold_task = PythonOperator(
        task_id='gold_aggregation',
        python_callable=log_to_mlflow,
    )

    # Task 4: Feature Engineering
    feature_task = PythonOperator(
        task_id='feature_engineering',
        python_callable=log_to_mlflow,
    )

    # Task 5: Model Training
    train_task = PythonOperator(
        task_id='model_training',
        python_callable=log_to_mlflow,
    )

    # 의존성 정의
    bronze_task >> silver_task >> gold_task >> feature_task >> train_task
```

#### 7.2 DAG 파일 배포

```bash
# DAG 파일을 dags/ 디렉토리에 복사
cp ml_pipeline_dag.py /home/i/work/ai/lakehouse-tick/dags/

# 권한 설정
sudo chown 50000:50000 /home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py

# Airflow에서 DAG 인식 확인 (약 30초 소요)
docker compose -f docker-compose-mlops.yml logs airflow-scheduler | grep ml_pipeline
```

#### 7.3 Airflow UI에서 DAG 활성화

1. http://localhost:8080 접속
2. Login: admin / admin
3. DAGs 페이지에서 `ml_pipeline` 찾기
4. Toggle 스위치 클릭하여 활성화
5. "Trigger DAG" 버튼으로 수동 실행

---

### 8️⃣ 중지 및 제거

#### 8.1 서비스 중지

```bash
# MLOps 스택만 중지 (데이터 유지)
docker compose -f docker-compose-mlops.yml stop

# Lakehouse 인프라는 계속 실행 상태 유지
docker compose ps
```

#### 8.2 MLOps 스택 완전 제거

```bash
# 컨테이너 + 네트워크 제거 (볼륨 유지)
docker compose -f docker-compose-mlops.yml down

# 컨테이너 + 네트워크 + 볼륨 모두 제거 (주의: 데이터 삭제)
docker compose -f docker-compose-mlops.yml down -v
```

#### 8.3 전체 스택 제거

```bash
# 1단계: MLOps 스택 제거
docker compose -f docker-compose-mlops.yml down -v

# 2단계: Lakehouse 인프라 제거
docker compose down -v

# 3단계: External 네트워크 제거
docker network rm lakehouse-net
```

---

### 9️⃣ Health Check 및 모니터링

#### 9.1 서비스 상태 확인

```bash
# MLOps 스택 헬스체크
docker compose -f docker-compose-mlops.yml ps

# 개별 서비스 헬스 확인
curl -f http://localhost:5000/health        # MLflow
curl -f http://localhost:8080/health        # Airflow
curl -f http://localhost:6379               # Redis (연결 테스트)

# PostgreSQL 확인
docker exec airflow-postgres pg_isready -U airflow -d airflow
```

#### 9.2 로그 확인

```bash
# MLflow 로그
docker compose -f docker-compose-mlops.yml logs -f mlflow

# Airflow Webserver 로그
docker compose -f docker-compose-mlops.yml logs -f airflow-webserver

# Airflow Scheduler 로그
docker compose -f docker-compose-mlops.yml logs -f airflow-scheduler

# 전체 로그
docker compose -f docker-compose-mlops.yml logs -f
```

#### 9.3 리소스 사용률 모니터링

```bash
# 실시간 리소스 모니터링
docker stats mlflow airflow-webserver airflow-scheduler airflow-postgres airflow-redis

# 디스크 사용량 확인
docker system df -v | grep -E 'mlflow|airflow'
```

---

### 🔟 트러블슈팅 가이드

#### 문제 1: External network not found

**증상**:
```
Error response from daemon: network lakehouse-net declared as external, but could not be found
```

**해결**:
```bash
# 네트워크 수동 생성
docker network create lakehouse-net

# 또는 기존 docker-compose.yml 먼저 시작
docker compose up -d
```

---

#### 문제 2: Airflow 초기화 실패

**증상**:
```
airflow.exceptions.AirflowConfigException: error: cannot use sqlite with the CeleryExecutor
```

**해결**:
```bash
# PostgreSQL 헬스체크 확인
docker compose -f docker-compose-mlops.yml ps airflow-postgres

# DB 초기화 재시도
docker compose -f docker-compose-mlops.yml run --rm airflow-webserver airflow db migrate
```

---

#### 문제 3: MLflow S3 연결 실패

**증상**:
```
botocore.exceptions.EndpointConnectionError: Could not connect to the endpoint URL
```

**해결**:
```bash
# SeaweedFS S3 상태 확인
docker compose ps seaweedfs-s3

# MLflow 컨테이너에서 네트워크 테스트
docker exec mlflow curl -f http://seaweedfs-s3:8333

# 환경 변수 확인
docker exec mlflow env | grep AWS
```

---

#### 문제 4: DAG 파일이 인식되지 않음

**증상**: Airflow UI에 DAG가 표시되지 않음

**해결**:
```bash
# 1. 파일 권한 확인
ls -l /home/i/work/ai/lakehouse-tick/dags/

# 2. 권한 수정
sudo chown -R 50000:50000 /home/i/work/ai/lakehouse-tick/dags/

# 3. Python 문법 에러 확인
docker exec airflow-scheduler python /opt/airflow/dags/ml_pipeline_dag.py

# 4. Scheduler 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler

# 5. 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-scheduler | tail -50
```

---

#### 문제 5: 메모리 부족

**증상**: Airflow 컨테이너가 자주 재시작됨

**해결**:
```bash
# 1. 현재 메모리 사용량 확인
docker stats --no-stream

# 2. docker-compose-mlops.yml에서 리소스 제약 조정
# deploy.resources.limits.memory를 2G → 4G로 증가

# 3. 불필요한 컨테이너 중지
docker compose -f docker-compose-mlops.yml stop airflow-worker  # Celery Worker 사용 안 할 경우
```

---

### 1️⃣1️⃣ 운영 팁

#### 11.1 자동 시작 설정

```bash
# docker-compose-mlops.yml의 모든 서비스에 추가
restart: unless-stopped
```

#### 11.2 백업 스크립트

```bash
#!/bin/bash
# backup-mlops.sh

BACKUP_DIR="/backups/mlops-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Airflow DB 백업
docker exec airflow-postgres pg_dump -U airflow airflow > $BACKUP_DIR/airflow-db.sql

# MLflow 데이터 백업
docker exec mlflow tar -czf - /mlflow > $BACKUP_DIR/mlflow-data.tar.gz

# DAG 파일 백업
tar -czf $BACKUP_DIR/dags.tar.gz /home/i/work/ai/lakehouse-tick/dags/

echo "✅ Backup completed: $BACKUP_DIR"
```

#### 11.3 모니터링 대시보드 추가

Grafana에 Airflow 메트릭 추가:

```yaml
# docker-compose-mlops.yml에 Prometheus Exporter 추가
airflow-exporter:
  image: pbweb/airflow-prometheus-exporter:latest
  container_name: airflow-exporter
  environment:
    AIRFLOW_PROMETHEUS_DATABASE_BACKEND: postgres
    AIRFLOW_PROMETHEUS_DATABASE_HOST: airflow-postgres
    AIRFLOW_PROMETHEUS_DATABASE_PORT: 5432
    AIRFLOW_PROMETHEUS_DATABASE_USER: airflow
    AIRFLOW_PROMETHEUS_DATABASE_PASSWORD: airflow
    AIRFLOW_PROMETHEUS_DATABASE_NAME: airflow
  ports:
    - "9112:9112"
  networks:
    - lakehouse-net
  depends_on:
    - airflow-postgres
```

---

### 1️⃣2️⃣ 성능 최적화

#### 12.1 Airflow 동시 실행 Task 수 증가

`docker-compose-mlops.yml`의 환경 변수 추가:

```yaml
environment:
  AIRFLOW__CORE__PARALLELISM: 32           # 전체 동시 실행 Task 수
  AIRFLOW__CORE__DAG_CONCURRENCY: 16       # DAG당 동시 실행 Task 수
  AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG: 3  # DAG당 최대 활성 Run 수
```

#### 12.2 MLflow 성능 튜닝

Production 환경에서는 SQLite 대신 PostgreSQL 사용:

```yaml
mlflow:
  command: >
    mlflow server
    --host 0.0.0.0
    --port 5000
    --backend-store-uri postgresql://mlflow:mlflow@mlflow-postgres:5432/mlflow
    --default-artifact-root s3://lakehouse/mlflow
```

---

### 1️⃣3️⃣ 체크리스트

#### 배포 전 확인

- [ ] `docker-compose.yml`에서 네트워크를 external로 변경
- [ ] `docker-compose-mlops.yml` 파일 생성
- [ ] `.env` 파일에 MLOps 환경 변수 추가
- [ ] `dags/`, `logs/`, `plugins/` 디렉토리 생성
- [ ] 디렉토리 권한 설정 (UID 50000)
- [ ] External 네트워크 `lakehouse-net` 존재 확인

#### 배포 중 확인

- [ ] 기존 Lakehouse 인프라 정상 실행 (`docker compose ps`)
- [ ] MLOps 스택 시작 (`docker compose -f docker-compose-mlops.yml up -d`)
- [ ] Airflow DB 초기화 (`airflow db migrate`)
- [ ] Admin 사용자 생성
- [ ] MLflow UI 접속 확인 (http://localhost:5000)
- [ ] Airflow UI 접속 확인 (http://localhost:8080)

#### 배포 후 확인

- [ ] 샘플 DAG 파일 작성 및 배포
- [ ] Airflow UI에서 DAG 인식 확인
- [ ] DAG 수동 실행 테스트
- [ ] MLflow에서 실험 로그 확인
- [ ] 네트워크 연결 테스트 (Airflow → MLflow, Airflow → Trino)
- [ ] 로그 파일 정상 생성 확인

---

### 1️⃣4️⃣ 다음 단계

1. **DAG 파일 확장**: 실제 Spark Job 연동 (`SparkSubmitOperator`)
2. **Slack 알림 설정**: Task 실패 시 Slack 알림
3. **모니터링 강화**: Prometheus + Grafana 대시보드 추가
4. **보안 강화**: RBAC 설정, SSL/TLS 적용
5. **백업 자동화**: Cron으로 정기 백업 스크립트 실행

---

**작성**: 2025-12-25
**버전**: 1.1 (옵션 2 구현 가이드 추가)
**다음 단계**: [GETTING_STARTED.md](../../GETTING_STARTED.md) - 빠른 시작 가이드
