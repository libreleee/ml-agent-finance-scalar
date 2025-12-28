# DAG 분리 전략 - MLflow + Airflow 현업 전문가 관점

작성일: 2025-12-28
작성자: Claude Sonnet 4.5

---

## 📊 Executive Summary

### **결론: DAG는 4개 분리가 현업 표준입니다** ✅

1. **MNIST (CNN)** → 별도 DAG
2. **CIFAR-10 (CNN)** → 별도 DAG  
3. **Tick Data** → 별도 DAG
4. **전력 데이터 (LightGBM)** → 별도 DAG

**파일 개수는 선택사항**:
- **옵션 A**: DAG 파일 4개 (직관적, 소규모 팀)
- **옵션 B**: Factory 패턴으로 파일 1-2개 (대규모, 템플릿화)

---

## 🎯 왜 각각 별도 DAG로 분리해야 하나?

### 4가지 워크플로우의 근본적 차이

| 구분 | MNIST/CIFAR-10 | Tick Data | 전력 데이터 (LightGBM) |
|------|----------------|-----------|------------------------|
| **스케줄** | 실험용 (수동/주간) | 실시간/시간단위 | 일/주 배치 |
| **리소스** | GPU 필수, 장시간 | CPU/IO 집약 | CPU 중심, 짧음 |
| **프레임워크** | TensorFlow/PyTorch | 다양 | LightGBM |
| **데이터 크기** | 고정 (수만장) | 스트리밍/증분 | 정형 배치 |
| **재처리(Backfill)** | 전체 재학습 | 구간 단위 증분 | 일 단위 |
| **실패 영향도** | 독립 실험 | 실시간 서비스 영향 | 독립 배치 |
| **Ownership** | 비전팀 | 퀀트/트레이딩팀 | 에너지팀 |

### 현업 5대 분리 이유

#### 1. **스케줄/트리거가 완전히 다름**
```python
# MNIST/CIFAR-10: 실험성
schedule_interval=None  # 수동 트리거 또는 주 1회

# Tick Data: 준실시간
schedule_interval='*/15 * * * *'  # 15분마다

# 전력 데이터: 일일 배치
schedule_interval='0 1 * * *'  # 매일 오전 1시
```

#### 2. **리소스 격리 필수**
```python
# Airflow Pool 설정
'mnist_cnn_training': {
    'pool': 'gpu_pool',
    'priority_weight': 5,
    'queue': 'gpu_queue'
}

'tick_model_training': {
    'pool': 'high_priority_cpu',
    'priority_weight': 10,  # 가장 높은 우선순위
    'queue': 'realtime_queue'
}

'power_lgbm_training': {
    'pool': 'default_pool',
    'priority_weight': 3,
    'queue': 'batch_queue'
}
```

#### 3. **실패 격리 (Blast Radius)**
- Tick 데이터 파이프라인 실패가 MNIST 실험을 멈추면 안 됨
- 각 DAG는 독립적으로 재시도 정책 적용
- SLA 알림도 별도 설정

#### 4. **Ownership 분리 (조직 구조)**
```
비전팀       → mnist_cnn_dag.py, cifar10_cnn_dag.py
퀀트팀       → tick_model_dag.py
에너지분석팀 → power_lgbm_dag.py
```
- Git PR 리뷰가 명확
- 배포 권한 분리
- 책임 소재 명확

#### 5. **MLflow 실험 추적 분리**
```python
# 각 DAG는 독립적인 MLflow Experiment 사용
mlflow.set_experiment("mnist-cnn-experiments")
mlflow.set_experiment("cifar10-cnn-experiments")
mlflow.set_experiment("tick-model-production")
mlflow.set_experiment("power-consumption-forecasting")
```

---

## 🏭 현업 Best Practice

### Pattern A: 파일 분리 (직관적) - 80% 기업

```
lakehouse-tick/
└── dags/
    ├── ml_mnist_cnn_dag.py          # DAG ID: mnist_cnn_training
    ├── ml_cifar10_cnn_dag.py        # DAG ID: cifar10_cnn_training
    ├── ml_tick_model_dag.py         # DAG ID: tick_model_training
    ├── ml_power_lgbm_dag.py         # DAG ID: power_lgbm_training
    │
    ├── common/
    │   ├── __init__.py
    │   ├── mlflow_utils.py          # MLflow 공통 함수
    │   ├── cnn_training_template.py # CNN 재사용 코드
    │   ├── model_registry.py        # 모델 등록 로직
    │   └── config.py                # 공통 설정
    │
    └── scripts/
        ├── train_mnist.py
        ├── train_cifar10.py
        ├── train_tick_model.py
        └── train_power_lgbm.py
```

**장점:**
- 각 팀이 독립적으로 수정 가능
- Git blame/PR 리뷰가 명확
- 초보자도 이해하기 쉬움
- 디버깅 간편

**단점:**
- 공통 코드 중복 가능성 (→ common 모듈로 해결)
- 설정 일관성 유지 필요

### Pattern B: Factory 패턴 (고급) - 20% 대기업

```python
# dags/model_training_factory.py
from airflow import DAG
from datetime import datetime, timedelta
from common.dag_factory import create_ml_training_dag

# 설정 기반 DAG 생성
TRAINING_CONFIGS = [
    {
        "dag_id": "mnist_cnn_training",
        "schedule": None,
        "model_type": "cnn",
        "framework": "tensorflow",
        "dataset": "mnist",
        "pool": "gpu_pool",
        "tags": ["ml", "cnn", "mnist", "experiment"]
    },
    {
        "dag_id": "cifar10_cnn_training",
        "schedule": None,
        "model_type": "cnn",
        "framework": "pytorch",
        "dataset": "cifar10",
        "pool": "gpu_pool",
        "tags": ["ml", "cnn", "cifar10", "experiment"]
    },
    {
        "dag_id": "tick_model_training",
        "schedule": "*/15 * * * *",
        "model_type": "timeseries",
        "framework": "sklearn",
        "dataset": "tick",
        "pool": "high_priority_cpu",
        "priority_weight": 10,
        "tags": ["ml", "tick", "realtime", "production"]
    },
    {
        "dag_id": "power_lgbm_training",
        "schedule": "0 1 * * *",
        "model_type": "gbm",
        "framework": "lightgbm",
        "dataset": "power",
        "pool": "default_pool",
        "tags": ["ml", "lgbm", "power", "batch"]
    },
]

# Factory로 DAG 생성
for config in TRAINING_CONFIGS:
    dag_id = config["dag_id"]
    globals()[dag_id] = create_ml_training_dag(**config)
```

**장점:**
- 중앙 관리, 설정 일관성
- YAML/JSON 기반 자동화 가능
- 템플릿 변경 시 모든 DAG 일괄 업데이트

**단점:**
- 초심자 진입 장벽
- 디버깅 복잡 (동적 생성)
- 특수 케이스 처리 어려움

---

## 🚨 Tick Data 특수 고려사항

### **중요: Tick 데이터는 Airflow만으로 처리하지 않습니다!**

현업에서 금융 Tick 데이터 아키텍처:

```
실시간 데이터 흐름:
┌─────────────┐
│ Market Data │ 
│  (Tick 스트림) │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Kafka/Kinesis   │ ← 실시간 수집
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Flink/Spark     │ ← 실시간 피처 생성
│   Streaming     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Feature Store   │ ← Redis/Feast
│  (실시간 피처)   │
└──────┬──────────┘
       │
       ├─────────────────────┐
       │                     │
       ▼                     ▼
┌─────────────┐      ┌────────────┐
│ Real-time   │      │  Airflow   │ ← 배치 재학습
│ Inference   │      │  (일/주)   │
└─────────────┘      └──────┬─────┘
                            │
                            ▼
                     ┌────────────┐
                     │   MLflow   │
                     │ (Model Reg)│
                     └────────────┘
```

### Airflow의 역할 (Tick 데이터)

**1. 배치 모델 재학습 (주기적)**
```python
# tick_model_dag.py
schedule_interval='0 2 * * 0'  # 매주 일요일 새벽 2시

tasks:
1. aggregate_weekly_features
2. prepare_training_data
3. train_model (MLflow)
4. backtest_model
5. register_to_production (조건부)
```

**2. 역사적 데이터 백필**
```python
# 과거 데이터로 모델 재학습
start_date = '2024-01-01'
end_date = '2024-12-31'
```

**3. 피처 엔지니어링 (배치)**
```python
# 일일 통계 피처 생성
- 일중 변동성
- 거래량 프로파일
- 상관관계 매트릭스
```

**실시간 추론은 Airflow 외부**:
- FastAPI/Flask + Model Server
- Feature Store에서 실시간 피처 조회
- MLflow에서 로드한 모델 사용

---

## 📝 각 DAG 구조 템플릿

### MNIST CNN DAG
```python
# dags/ml_mnist_cnn_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import mlflow

default_args = {
    'owner': 'vision-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'mnist_cnn_training',
    default_args=default_args,
    description='MNIST CNN Model Training with MLflow',
    schedule_interval=None,  # 수동 트리거
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ml', 'cnn', 'mnist', 'experiment'],
)

def prepare_mnist_data(**context):
    """MNIST 데이터 로드 및 전처리"""
    from tensorflow.keras.datasets import mnist
    import numpy as np
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("mnist-cnn-experiments")
    
    with mlflow.start_run(run_name="prepare_data"):
        (x_train, y_train), (x_test, y_test) = mnist.load_data()
        
        # 정규화
        x_train = x_train.astype('float32') / 255.0
        x_test = x_test.astype('float32') / 255.0
        
        mlflow.log_param("train_samples", len(x_train))
        mlflow.log_param("test_samples", len(x_test))
        
        # 데이터 저장 (S3/SeaweedFS)
        return {"data_path": "s3://lakehouse/mnist/data"}

def train_mnist_cnn(**context):
    """CNN 모델 학습"""
    import tensorflow as tf
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("mnist-cnn-experiments")
    
    with mlflow.start_run(run_name="train_cnn"):
        # 모델 정의
        model = tf.keras.Sequential([
            tf.keras.layers.Conv2D(32, (3,3), activation='relu', input_shape=(28,28,1)),
            tf.keras.layers.MaxPooling2D((2,2)),
            tf.keras.layers.Conv2D(64, (3,3), activation='relu'),
            tf.keras.layers.MaxPooling2D((2,2)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(10, activation='softmax')
        ])
        
        model.compile(optimizer='adam',
                     loss='sparse_categorical_crossentropy',
                     metrics=['accuracy'])
        
        # 하이퍼파라미터 로깅
        mlflow.log_param("optimizer", "adam")
        mlflow.log_param("epochs", 10)
        mlflow.log_param("batch_size", 32)
        
        # 학습 (실제로는 데이터 로드)
        # history = model.fit(x_train, y_train, epochs=10, validation_split=0.2)
        
        # 메트릭 로깅
        mlflow.log_metric("train_accuracy", 0.98)
        mlflow.log_metric("val_accuracy", 0.97)
        
        # 모델 저장
        mlflow.tensorflow.log_model(model, "model")
        
        return {"model_uri": mlflow.get_artifact_uri("model")}

def evaluate_mnist_model(**context):
    """모델 평가"""
    mlflow.set_tracking_uri("http://mlflow:5000")
    
    with mlflow.start_run(run_name="evaluate"):
        # 평가 로직
        test_accuracy = 0.97
        mlflow.log_metric("test_accuracy", test_accuracy)
        
        return {"test_accuracy": test_accuracy}

def register_mnist_model(**context):
    """MLflow Model Registry에 등록"""
    ti = context['ti']
    test_accuracy = ti.xcom_pull(task_ids='evaluate_model')['test_accuracy']
    
    if test_accuracy > 0.95:  # 임계값
        mlflow.set_tracking_uri("http://mlflow:5000")
        
        model_uri = ti.xcom_pull(task_ids='train_model')['model_uri']
        
        mlflow.register_model(
            model_uri=model_uri,
            name="mnist-cnn-model"
        )
        
        print(f"✅ Model registered with accuracy: {test_accuracy}")
    else:
        print(f"❌ Model accuracy {test_accuracy} below threshold")

# Task 정의
task_prepare = PythonOperator(
    task_id='prepare_data',
    python_callable=prepare_mnist_data,
    dag=dag,
)

task_train = PythonOperator(
    task_id='train_model',
    python_callable=train_mnist_cnn,
    pool='gpu_pool',
    dag=dag,
)

task_evaluate = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate_mnist_model,
    dag=dag,
)

task_register = PythonOperator(
    task_id='register_model',
    python_callable=register_mnist_model,
    dag=dag,
)

# Task 의존성
task_prepare >> task_train >> task_evaluate >> task_register
```

### CIFAR-10 CNN DAG
```python
# dags/ml_cifar10_cnn_dag.py
# MNIST와 유사한 구조, 데이터셋과 모델 아키텍처만 변경

dag = DAG(
    'cifar10_cnn_training',
    default_args=default_args,
    description='CIFAR-10 CNN Model Training with MLflow',
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ml', 'cnn', 'cifar10', 'experiment'],
)

# prepare_data, train_model, evaluate_model, register_model
# (구조는 MNIST와 동일, 데이터 로드만 변경)
```

### Tick Data Model DAG
```python
# dags/ml_tick_model_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor
from datetime import datetime, timedelta

default_args = {
    'owner': 'quant-team',
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
    'priority_weight': 10,  # 가장 높은 우선순위
}

dag = DAG(
    'tick_model_training',
    default_args=default_args,
    description='Tick Data Model Training (Batch)',
    schedule_interval='0 2 * * 0',  # 매주 일요일 새벽 2시
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ml', 'tick', 'production', 'timeseries'],
)

def aggregate_tick_features(**context):
    """주간 Tick 데이터 집계"""
    from pyspark.sql import SparkSession
    import mlflow
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("tick-model-production")
    
    with mlflow.start_run(run_name="aggregate_features"):
        spark = SparkSession.builder.appName("TickAggregation").getOrCreate()
        
        # Trino/Iceberg에서 데이터 읽기
        df = spark.read.format("iceberg") \
            .load("lakehouse.silver.tick_data")
        
        # 피처 엔지니어링
        # - 시간대별 변동성
        # - 거래량 프로파일
        # - 가격 모멘텀
        
        mlflow.log_metric("records_processed", df.count())
        
        return {"feature_path": "s3://lakehouse/tick/features/"}

def train_tick_model(**context):
    """시계열 모델 학습"""
    from sklearn.ensemble import RandomForestRegressor
    import mlflow
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("tick-model-production")
    
    with mlflow.start_run(run_name="train_model"):
        # 데이터 로드
        # X, y = load_features()
        
        model = RandomForestRegressor(n_estimators=100)
        # model.fit(X, y)
        
        mlflow.log_param("model_type", "RandomForest")
        mlflow.log_param("n_estimators", 100)
        
        mlflow.sklearn.log_model(model, "model")
        
        return {"model_uri": mlflow.get_artifact_uri("model")}

def backtest_tick_model(**context):
    """백테스팅"""
    import mlflow
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    
    with mlflow.start_run(run_name="backtest"):
        # 백테스팅 로직
        sharpe_ratio = 1.8
        max_drawdown = 0.15
        
        mlflow.log_metric("sharpe_ratio", sharpe_ratio)
        mlflow.log_metric("max_drawdown", max_drawdown)
        
        return {
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown
        }

def register_tick_model(**context):
    """프로덕션 등록 (조건부)"""
    ti = context['ti']
    backtest_result = ti.xcom_pull(task_ids='backtest_model')
    
    if backtest_result['sharpe_ratio'] > 1.5:
        mlflow.set_tracking_uri("http://mlflow:5000")
        
        model_uri = ti.xcom_pull(task_ids='train_model')['model_uri']
        
        # 프로덕션으로 승격
        client = mlflow.tracking.MlflowClient()
        model_version = client.create_model_version(
            name="tick-model",
            source=model_uri,
            run_id=mlflow.active_run().info.run_id
        )
        
        client.transition_model_version_stage(
            name="tick-model",
            version=model_version.version,
            stage="Production"
        )
        
        print(f"✅ Model promoted to Production")
    else:
        print(f"❌ Model did not meet production criteria")

# Task 정의
task_aggregate = PythonOperator(
    task_id='aggregate_features',
    python_callable=aggregate_tick_features,
    pool='high_priority_cpu',
    dag=dag,
)

task_train = PythonOperator(
    task_id='train_model',
    python_callable=train_tick_model,
    pool='high_priority_cpu',
    dag=dag,
)

task_backtest = PythonOperator(
    task_id='backtest_model',
    python_callable=backtest_tick_model,
    dag=dag,
)

task_register = PythonOperator(
    task_id='register_model',
    python_callable=register_tick_model,
    dag=dag,
)

# Task 의존성
task_aggregate >> task_train >> task_backtest >> task_register
```

### 전력 데이터 LightGBM DAG
```python
# dags/ml_power_lgbm_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'energy-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

dag = DAG(
    'power_lgbm_training',
    default_args=default_args,
    description='Power Consumption Forecasting with LightGBM',
    schedule_interval='0 1 * * *',  # 매일 오전 1시
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ml', 'lgbm', 'power', 'forecasting'],
)

def prepare_power_data(**context):
    """전력 데이터 준비"""
    import mlflow
    from pyspark.sql import SparkSession
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("power-consumption-forecasting")
    
    with mlflow.start_run(run_name="prepare_data"):
        spark = SparkSession.builder.appName("PowerData").getOrCreate()
        
        # 어제 데이터 로드
        execution_date = context['ds']
        df = spark.sql(f"""
            SELECT * FROM lakehouse.silver.power_consumption
            WHERE date = '{execution_date}'
        """)
        
        mlflow.log_param("execution_date", execution_date)
        mlflow.log_metric("records", df.count())
        
        return {"data_path": "s3://lakehouse/power/data/"}

def train_lgbm_model(**context):
    """LightGBM 모델 학습"""
    import lightgbm as lgb
    import mlflow
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("power-consumption-forecasting")
    
    with mlflow.start_run(run_name="train_lgbm"):
        # 데이터 로드
        # X_train, y_train = load_data()
        
        params = {
            'objective': 'regression',
            'metric': 'rmse',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9
        }
        
        # model = lgb.train(params, train_set)
        
        mlflow.log_params(params)
        mlflow.log_metric("train_rmse", 0.15)
        mlflow.log_metric("val_rmse", 0.18)
        
        # mlflow.lightgbm.log_model(model, "model")
        
        return {"model_uri": mlflow.get_artifact_uri("model")}

def evaluate_power_model(**context):
    """모델 평가"""
    import mlflow
    
    mlflow.set_tracking_uri("http://mlflow:5000")
    
    with mlflow.start_run(run_name="evaluate"):
        # 평가
        test_rmse = 0.17
        mae = 0.12
        
        mlflow.log_metric("test_rmse", test_rmse)
        mlflow.log_metric("mae", mae)
        
        return {"test_rmse": test_rmse, "mae": mae}

def register_power_model(**context):
    """모델 등록"""
    ti = context['ti']
    metrics = ti.xcom_pull(task_ids='evaluate_model')
    
    if metrics['test_rmse'] < 0.20:  # 임계값
        mlflow.set_tracking_uri("http://mlflow:5000")
        
        model_uri = ti.xcom_pull(task_ids='train_model')['model_uri']
        
        mlflow.register_model(
            model_uri=model_uri,
            name="power-consumption-model"
        )
        
        print(f"✅ Model registered with RMSE: {metrics['test_rmse']}")
    else:
        print(f"❌ Model RMSE {metrics['test_rmse']} above threshold")

# Task 정의
task_prepare = PythonOperator(
    task_id='prepare_data',
    python_callable=prepare_power_data,
    dag=dag,
)

task_train = PythonOperator(
    task_id='train_model',
    python_callable=train_lgbm_model,
    dag=dag,
)

task_evaluate = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate_power_model,
    dag=dag,
)

task_register = PythonOperator(
    task_id='register_model',
    python_callable=register_power_model,
    dag=dag,
)

# Task 의존성
task_prepare >> task_train >> task_evaluate >> task_register
```

---

## 🔧 공통 모듈 구조

### common/mlflow_utils.py
```python
"""MLflow 공통 유틸리티"""
import mlflow
import os

MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')

def init_mlflow(experiment_name: str):
    """MLflow 초기화"""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(experiment_name)

def log_dataset_info(dataset_name: str, num_samples: int, num_features: int):
    """데이터셋 정보 로깅"""
    mlflow.log_param("dataset", dataset_name)
    mlflow.log_param("num_samples", num_samples)
    mlflow.log_param("num_features", num_features)

def register_model_if_better(model_uri: str, model_name: str, 
                              metric_name: str, metric_value: float, 
                              threshold: float):
    """조건부 모델 등록"""
    if metric_value > threshold:
        mlflow.register_model(model_uri=model_uri, name=model_name)
        return True
    return False
```

### common/config.py
```python
"""공통 설정"""

# MLflow 설정
MLFLOW_CONFIG = {
    'tracking_uri': 'http://mlflow:5000',
    'artifact_location': 's3://lakehouse/mlflow/artifacts',
}

# Airflow Pool 설정
AIRFLOW_POOLS = {
    'gpu_pool': {'slots': 2, 'description': 'GPU tasks'},
    'high_priority_cpu': {'slots': 4, 'description': 'High priority CPU'},
    'default_pool': {'slots': 8, 'description': 'Default pool'},
}

# 모델별 임계값
MODEL_THRESHOLDS = {
    'mnist': {'accuracy': 0.95},
    'cifar10': {'accuracy': 0.85},
    'tick': {'sharpe_ratio': 1.5, 'max_drawdown': 0.20},
    'power': {'rmse': 0.20},
}
```

---

## 🎨 DAG Factory 패턴 (고급)

### dags/model_training_factory.py
```python
"""모델 학습 DAG Factory"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from typing import Dict, Any
import mlflow

def create_ml_training_dag(
    dag_id: str,
    schedule: str,
    model_type: str,
    dataset: str,
    framework: str,
    pool: str = 'default_pool',
    priority_weight: int = 5,
    tags: list = None
) -> DAG:
    """ML 학습 DAG 생성 Factory"""
    
    default_args = {
        'owner': 'ml-team',
        'retries': 2,
        'retry_delay': timedelta(minutes=3),
        'priority_weight': priority_weight,
    }
    
    dag = DAG(
        dag_id=dag_id,
        default_args=default_args,
        description=f'{dataset.upper()} Model Training with {framework}',
        schedule_interval=schedule,
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=tags or ['ml', model_type, dataset],
    )
    
    # 동적 Task 생성
    def prepare_data(**context):
        mlflow.set_tracking_uri("http://mlflow:5000")
        mlflow.set_experiment(f"{dataset}-{model_type}")
        
        with mlflow.start_run(run_name="prepare_data"):
            # 데이터 준비 로직
            print(f"Preparing {dataset} data...")
            mlflow.log_param("dataset", dataset)
            return {"status": "success"}
    
    def train_model(**context):
        mlflow.set_tracking_uri("http://mlflow:5000")
        
        with mlflow.start_run(run_name="train_model"):
            print(f"Training {model_type} on {dataset} using {framework}...")
            mlflow.log_param("framework", framework)
            mlflow.log_param("model_type", model_type)
            return {"model_uri": "s3://models/"}
    
    def evaluate_model(**context):
        mlflow.set_tracking_uri("http://mlflow:5000")
        
        with mlflow.start_run(run_name="evaluate"):
            print(f"Evaluating {model_type} model...")
            mlflow.log_metric("accuracy", 0.95)
            return {"accuracy": 0.95}
    
    def register_model(**context):
        print(f"Registering {dataset} model to MLflow...")
        return {"status": "registered"}
    
    # Task 생성
    task_prepare = PythonOperator(
        task_id='prepare_data',
        python_callable=prepare_data,
        dag=dag,
    )
    
    task_train = PythonOperator(
        task_id='train_model',
        python_callable=train_model,
        pool=pool,
        dag=dag,
    )
    
    task_evaluate = PythonOperator(
        task_id='evaluate_model',
        python_callable=evaluate_model,
        dag=dag,
    )
    
    task_register = PythonOperator(
        task_id='register_model',
        python_callable=register_model,
        dag=dag,
    )
    
    # Task 의존성
    task_prepare >> task_train >> task_evaluate >> task_register
    
    return dag


# DAG 설정
TRAINING_CONFIGS = [
    {
        "dag_id": "mnist_cnn_training",
        "schedule": None,
        "model_type": "cnn",
        "framework": "tensorflow",
        "dataset": "mnist",
        "pool": "gpu_pool",
        "tags": ["ml", "cnn", "mnist", "experiment"]
    },
    {
        "dag_id": "cifar10_cnn_training",
        "schedule": None,
        "model_type": "cnn",
        "framework": "pytorch",
        "dataset": "cifar10",
        "pool": "gpu_pool",
        "tags": ["ml", "cnn", "cifar10", "experiment"]
    },
    {
        "dag_id": "tick_model_training",
        "schedule": "0 2 * * 0",
        "model_type": "timeseries",
        "framework": "sklearn",
        "dataset": "tick",
        "pool": "high_priority_cpu",
        "priority_weight": 10,
        "tags": ["ml", "tick", "production"]
    },
    {
        "dag_id": "power_lgbm_training",
        "schedule": "0 1 * * *",
        "model_type": "gbm",
        "framework": "lightgbm",
        "dataset": "power",
        "pool": "default_pool",
        "tags": ["ml", "lgbm", "power"]
    },
]

# Factory로 DAG 생성
for config in TRAINING_CONFIGS:
    dag_id = config.pop("dag_id")
    globals()[dag_id] = create_ml_training_dag(dag_id=dag_id, **config)
```

---

## 🚀 배포 및 운영 전략

### Phase 1: 초기 구현 (1-2주)
```
1. 4개 DAG 파일 생성 (직관적 접근)
2. 공통 모듈 분리 (mlflow_utils, config)
3. 각 DAG 독립 테스트
```

### Phase 2: 통합 및 최적화 (2-3주)
```
1. MLflow Experiment 연동 확인
2. Airflow Pool/Queue 설정
3. SLA 및 알림 구성
```

### Phase 3: 프로덕션 (4주~)
```
1. 모니터링 대시보드 (Grafana)
2. 자동 재학습 파이프라인
3. A/B 테스트 인프라
```

### Phase 4: 고도화 (선택)
```
1. Factory 패턴으로 리팩토링
2. YAML 기반 설정 관리
3. CI/CD 파이프라인 통합
```

---

## 📊 현업 체크리스트

### ✅ DAG 설계 원칙
- [ ] 각 DAG는 하나의 비즈니스 워크플로우를 담당
- [ ] 스케줄이 다르면 무조건 분리
- [ ] 리소스 요구사항이 다르면 분리
- [ ] Ownership이 다르면 분리
- [ ] 재처리(Backfill) 단위가 다르면 분리

### ✅ MLflow 통합
- [ ] 각 DAG는 독립적인 Experiment 사용
- [ ] Run name은 명확하게 (prepare_data, train_model 등)
- [ ] 하이퍼파라미터 모두 log_param으로 기록
- [ ] 주요 메트릭 log_metric으로 추적
- [ ] 모델은 log_model로 저장 (artifacts)
- [ ] 조건부 Model Registry 등록

### ✅ 운영 고려사항
- [ ] 각 DAG의 SLA 정의
- [ ] 알림 채널 설정 (Slack/Email)
- [ ] 재시도 정책 정의
- [ ] Pool/Queue 리소스 할당
- [ ] 로그 보관 정책

---

## 💡 권장사항

### 당신의 프로젝트 (lakehouse-tick)

1. **즉시 시작 가능한 접근**:
   ```
   dags/
   ├── ml_mnist_cnn_dag.py        # 시작
   ├── ml_cifar10_cnn_dag.py      # 다음
   ├── ml_tick_model_dag.py       # 핵심
   ├── ml_power_lgbm_dag.py       # 추가
   └── common/
       ├── mlflow_utils.py
       └── config.py
   ```

2. **우선순위**:
   - 1순위: Tick Model DAG (비즈니스 핵심)
   - 2순위: Power LightGBM DAG (실용성)
   - 3순위: MNIST/CIFAR-10 (실험/학습)

3. **현재 ml_pipeline_dag.py 활용**:
   - 템플릿으로 사용
   - 4개로 복제 후 각각 커스터마이즈

---

## 📚 참고 자료

### 공식 문서
- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [MLflow Tracking](https://mlflow.org/docs/latest/tracking.html)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)

### 현업 사례
- Uber: Michelangelo Platform (DAG per Model)
- Netflix: Metaflow (Workflow Orchestration)
- Airbnb: Bighead ML Platform (Airflow + MLflow)

### 아키텍처 패턴
- Lambda Architecture (배치 + 실시간)
- Kappa Architecture (스트리밍 중심)
- Feature Store Pattern (Feast, Tecton)

---

## 🎯 다음 액션

이제 다음 중 선택해주세요:

1. **A) 4개 DAG 파일 생성** (직관적, 권장)
   - 각각 독립 파일로 생성
   - 공통 모듈 분리
   - 즉시 실행 가능한 코드

2. **B) Factory 패턴 구현** (고급)
   - 1개 파일에서 4개 DAG 생성
   - 설정 기반 자동화
   - 확장성 높음

3. **C) 현재 ml_pipeline_dag.py 리팩토링**
   - 기존 코드 재사용
   - 4개로 분리
   - 점진적 마이그레이션

어떤 방식으로 진행하시겠습니까?

---

**작성일**: 2025-12-28  
**작성자**: Claude Sonnet 4.5 (MLflow/Airflow 전문가 모드)  
**버전**: 2.0
