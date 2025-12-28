# ML/DL 모델 구현 가이드

## 📋 목차

1. [사전 준비](#사전-준비)
2. [1단계: 의존성 추가](#1단계-의존성-추가)
3. [2단계: Docker 설정 변경](#2단계-docker-설정-변경)
4. [3단계: Airflow DAG 작성](#3단계-airflow-dag-작성)
5. [4단계: MLflow 통합](#4단계-mlflow-통합)
6. [5단계: 테스트 및 검증](#5단계-테스트-및-검증)
7. [트러블슈팅](#트러블슈팅)

---

## 사전 준비

### 확인 사항

```bash
# 현재 디렉토리
cd /home/i/work/ai/lakehouse-tick

# MLOps 스택 실행 확인
docker compose -f docker-compose-mlops.yml ps

# Airflow UI: http://localhost:8082 (admin/admin)
# MLflow UI: http://localhost:5000
```

### 백업

```bash
# 기존 설정 백업
cp requirements-airflow.txt requirements-airflow.txt.backup
cp docker-compose-mlops.yml docker-compose-mlops.yml.backup
```

---

## 1단계: 의존성 추가

### 파일: requirements-airflow.txt

위치: `/home/i/work/ai/lakehouse-tick/requirements-airflow.txt`

#### Traditional ML 라이브러리 추가

기존 내용 아래에 추가:

```txt
# ============ NEW: Traditional ML ============
xgboost>=2.0.3
lightgbm>=4.1.0
```

#### Deep Learning 라이브러리 추가

```txt
# ============ NEW: Deep Learning ============
# TensorFlow/Keras
tensorflow>=2.15.0,<2.16.0
keras>=3.0.0

# PyTorch
torch>=2.1.0,<2.3.0
torchvision>=0.16.0

# Compatibility
numpy>=1.23.0,<2.0.0
protobuf>=3.19.0,<4.0.0
```

---

## 2단계: Docker 설정 변경

### 파일: docker-compose-mlops.yml

위치: `/home/i/work/ai/lakehouse-tick/docker-compose-mlops.yml`

#### 2.1 Airflow Worker 리소스 증가

`airflow-worker` 섹션에 `deploy` 블록 추가:

```yaml
airflow-worker:
  <<: *airflow-common
  command: celery worker

  # 아래 추가
  deploy:
    resources:
      limits:
        cpus: '6'      # CPU 증가: 2 → 6
        memory: 8G     # 메모리 증가: 2G → 8G
      reservations:
        cpus: '4'
        memory: 6G
  # 여기까지

  healthcheck:
    test: ["CMD-SHELL", 'celery --app airflow.providers.celery.executors.celery_executor.app inspect ping -d "celery@$${HOSTNAME}"']
    interval: 30s
    timeout: 10s
    retries: 5
  environment:
    <<: *airflow-common-env
    DUMB_INIT_SETSID: "0"
  restart: always
  depends_on:
    <<: *airflow-common-depends-on
    airflow-init:
      condition: service_completed_successfully
```

#### 2.2 변경 사항 적용

```bash
# 1. MLOps 스택 중지
docker compose -f docker-compose-mlops.yml down

# 2. Airflow 이미지 재빌드 (requirements-airflow.txt 변경 반영)
docker compose -f docker-compose-mlops.yml build --no-cache airflow-worker

# 3. MLOps 스택 재시작
docker compose -f docker-compose-mlops.yml up -d

# 4. 로그 확인 (라이브러리 설치 확인)
docker compose -f docker-compose-mlops.yml logs -f airflow-worker
```

#### 2.3 설치 확인

```bash
# Worker 컨테이너 접속
docker compose -f docker-compose-mlops.yml exec airflow-worker bash

# 라이브러리 확인
python -c "import xgboost; print(f'XGBoost: {xgboost.__version__}')"
python -c "import lightgbm; print(f'LightGBM: {lightgbm.__version__}')"
python -c "import tensorflow as tf; print(f'TensorFlow: {tf.__version__}')"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"

# 예상 출력:
# XGBoost: 2.0.3
# LightGBM: 4.1.0
# TensorFlow: 2.15.x
# PyTorch: 2.1.x
```

---

## 3단계: Airflow DAG 작성

### 3.1 DAG 파일 위치

모든 DAG 파일은 다음 디렉토리에 생성:

```
/home/i/work/ai/lakehouse-tick/dags/
```

### 3.2 기존 DAG 참조

참조 파일: `/home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py`

기존 구조를 참고하여 새로운 DAG 작성

### 3.3 DAG 작성 패턴

모든 DAG는 다음 패턴을 따릅니다:

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
import os

# MLflow 추적 URI
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')

# 기본 인자
default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG 정의
dag = DAG(
    'model_name_pipeline',  # DAG ID
    default_args=default_args,
    description='Model description',
    schedule=timedelta(days=1),
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['ml', 'model-type', 'mlflow'],
)

# Task 정의
def task_name(**context):
    """Task description"""
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with mlflow.start_run(run_name="task_name"):
        # Task 로직
        mlflow.log_param("param_name", param_value)
        mlflow.log_metric("metric_name", metric_value)

        return {"result": "value"}

# Task 인스턴스화
task = PythonOperator(
    task_id='task_name',
    python_callable=task_name,
    dag=dag,
)
```

### 3.4 생성할 DAG 파일들

- `xgboost_pipeline_dag.py` - XGBoost 분류
- `lightgbm_pipeline_dag.py` - LightGBM 분류
- `tensorflow_mnist_mlp_dag.py` - TensorFlow MNIST MLP
- `tensorflow_mnist_cnn_dag.py` - TensorFlow MNIST CNN
- `pytorch_mnist_mlp_dag.py` - PyTorch MNIST MLP
- `pytorch_mnist_cnn_dag.py` - PyTorch MNIST CNN

자세한 코드 예제는 [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md) 참조

---

## 4단계: MLflow 통합

### 4.1 Autologging 설정

각 프레임워크별 autologging 활성화:

```python
# XGBoost
import mlflow.xgboost
mlflow.xgboost.autolog()

# LightGBM
import mlflow.lightgbm
mlflow.lightgbm.autolog()

# TensorFlow/Keras
import mlflow.tensorflow
mlflow.tensorflow.autolog()

# PyTorch
import mlflow.pytorch
mlflow.pytorch.autolog()
```

### 4.2 Manual Logging

```python
with mlflow.start_run(run_name="experiment_name"):
    # 파라미터 로깅
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_param("batch_size", 128)
    mlflow.log_param("epochs", 10)

    # 메트릭 로깅
    mlflow.log_metric("train_accuracy", 0.95)
    mlflow.log_metric("test_accuracy", 0.93)
    mlflow.log_metric("loss", 0.05)

    # 아티팩트 로깅
    mlflow.log_artifact("model_summary.txt")

    # 모델 로깅
    mlflow.sklearn.log_model(model, "model")
```

### 4.3 모델 레지스트리

```python
# 최신 run 가져오기
experiment = mlflow.get_experiment_by_name("Default")
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
latest_run_id = runs.iloc[0]['run_id']

# 모델 등록
model_uri = f"runs:/{latest_run_id}/model"
mlflow.register_model(model_uri, "model_name")

# 모델 stage 변경
client = mlflow.MlflowClient()
client.transition_model_version_stage(
    name="model_name",
    version=1,
    stage="Production"
)
```

---

## 5단계: 테스트 및 검증

### 5.1 DAG 문법 체크

```bash
# DAG 파일 테스트
docker compose -f docker-compose-mlops.yml exec airflow-worker \
    airflow dags test xgboost_classification_pipeline 2025-12-27
```

### 5.2 Airflow UI에서 확인

1. Airflow UI 접속: http://localhost:8082
2. DAG 목록에서 새 DAG 확인
3. DAG 활성화 (토글 스위치)
4. "Trigger DAG" 클릭하여 수동 실행

### 5.3 MLflow UI에서 확인

1. MLflow UI 접속: http://localhost:5000
2. Experiments 탭에서 실험 확인
3. Runs 탭에서 메트릭/파라미터 확인
4. Models 탭에서 등록된 모델 확인

### 5.4 로그 확인

```bash
# Airflow task 로그
docker compose -f docker-compose-mlops.yml logs -f airflow-worker | grep -i "task_id\|error\|✅"

# MLflow 로그
docker compose -f docker-compose-mlops.yml logs -f mlflow
```

---

## 트러블슈팅

### 문제 1: 메모리 부족

**증상**:
```
MemoryError: Unable to allocate array
RuntimeError: CUDA out of memory
```

**해결**:
1. Docker 메모리 제한 증가
2. 배치 크기 감소
3. 에포크 수 감소

```yaml
# docker-compose-mlops.yml
airflow-worker:
  deploy:
    resources:
      limits:
        memory: 8G  # 더 증가
```

### 문제 2: TensorFlow CPU 경고

**증상**:
```
This TensorFlow binary is optimized with oneAPI Deep Neural Network Library (oneDNN)
I tensorflow/cc/client/client_session.cc:305] Your CPU supports instructions that this TensorFlow binary was not compiled to use
```

**해결**: 무시해도 됨 (성능 최적화 관련 정보성 메시지)

### 문제 3: PyTorch CUDA 관련 경고

**증상**:
```
UserWarning: CUDA not available, using CPU
```

**해결**: 정상 (GPU 없는 환경에서 예상되는 동작)

### 문제 4: DAG가 UI에 나타나지 않음

**원인**: DAG 파일 문법 오류

**해결**:
```bash
# 문법 체크
python /home/i/work/ai/lakehouse-tick/dags/your_dag.py
```

### 문제 5: MLflow 연결 실패

**증상**:
```
mlflow.exceptions.MlflowException: Failed to connect to MLflow
```

**해결**:
```python
# MLFLOW_TRACKING_URI 확인
MLFLOW_TRACKING_URI = 'http://mlflow:5000'  # 컨테이너 내부
# 또는
MLFLOW_TRACKING_URI = 'http://localhost:5000'  # 호스트
```

### 문제 6: 라이브러리 import 에러

**증상**:
```
ModuleNotFoundError: No module named 'xgboost'
```

**해결**:
```bash
# 이미지 재빌드
docker compose -f docker-compose-mlops.yml build --no-cache airflow-worker
docker compose -f docker-compose-mlops.yml up -d

# 설치 확인
docker compose -f docker-compose-mlops.yml exec airflow-worker \
    python -c "import xgboost; print(xgboost.__version__)"
```

### 문제 7: Task timeout

**증상**:
```
airflow.exceptions.AirflowTaskTimeout: Task exited after max_tries attempts
```

**해결**:
```python
# DAG의 default_args에서 timeout 증가
default_args = {
    'execution_timeout': timedelta(hours=3),  # 3시간으로 증가
}
```

---

**다음**: [모델 사양 읽기 →](03-MODEL_SPECIFICATIONS.md)
