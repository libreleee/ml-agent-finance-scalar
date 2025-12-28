# Airflow DAG 분리 전략 - 각각 별도 DAG 파일 만들기 (Claude Sonnet 4.5)

**작성일**: 2025-12-27
**작성자**: Claude Sonnet 4.5
**문서 목적**: MNIST, CIFAR-10, Tick 데이터, 가정집 전력 4가지 모델 학습을 위한 DAG 설계 설명

---

## 🎯 핵심 질문과 답변

### Q: "각각의 DAG 파일을 만들어야 해?"

**A: 네, 각 모델마다 별도의 DAG 파일을 만드는 것을 강력히 권장합니다.** ✅

---

## 📌 왜 각각 별도 DAG 파일인가?

### 1️⃣ 독립적인 실행 및 관리

각 모델은 **완전히 다른 목적, 데이터, 주기**를 가집니다:

| DAG | 데이터셋 | 모델 타입 | 목적 | 실행 주기 | 데이터 특성 |
|-----|---------|---------|------|---------|-----------|
| **mnist_cnn_dag.py** | 손글씨 숫자 (28×28) | CNN | 숫자 분류 (0-9) | 주 1회 | 고정 데이터셋 |
| **cifar10_dag.py** | 10종 이미지 (32×32) | CNN/ResNet | 이미지 분류 | 주 1회 | 고정 데이터셋 |
| **tick_data_dag.py** | 금융 Tick 시계열 | LSTM/GRU | 가격 예측 | **매일** | 매일 새 데이터 |
| **household_power_dag.py** | 전력 소비량 | LightGBM | 소비량 예측 | **매일** | 매일 새 데이터 |

**핵심 이유**:
- ✅ **스케줄링이 다름**: MNIST/CIFAR는 주 1회, Tick/전력은 매일
- ✅ **데이터 소스가 다름**: MNIST는 Keras 다운로드, Tick은 데이터베이스
- ✅ **모델 아키텍처가 다름**: CNN vs LSTM vs LightGBM
- ✅ **오류 격리 필요**: 한 모델 실패가 다른 모델에 영향 주면 안됨

---

### 2️⃣ 오류 격리 (Fault Isolation)

#### ❌ 나쁜 예: 하나의 DAG에 모두 포함
```python
# all_models_dag.py (비권장)
dag = DAG('all_models_training', ...)

mnist_task >> cifar10_task >> tick_task >> power_task
```

**문제점**:
```
mnist_task [성공] ✅
  ↓
cifar10_task [성공] ✅
  ↓
tick_task [실패] ❌ ← 데이터베이스 연결 오류
  ↓
power_task [실행 안됨] ⏸️ ← tick_task 실패로 인해 실행조차 안됨!
```

#### ✅ 좋은 예: 개별 DAG
```python
# 4개의 독립 DAG 파일
mnist_cnn_dag.py     → [성공] ✅
cifar10_dag.py       → [성공] ✅
tick_data_dag.py     → [실패] ❌ (이 DAG만 영향)
household_power_dag.py → [성공] ✅ (영향 없음)
```

**장점**:
- ✅ tick_data_dag 실패해도 다른 DAG는 정상 실행
- ✅ 오류 발생 시 해당 DAG만 재실행
- ✅ 독립적인 모니터링 가능

---

### 3️⃣ 각 모델의 특수한 요구사항

각 모델은 **완전히 다른 Task 구성**이 필요합니다:

#### 🔢 MNIST CNN DAG
```
Tasks:
1. download_mnist_data        # tensorflow.keras.datasets.mnist
   ↓
2. normalize_images           # 0-1 정규화, reshape (28,28,1)
   ↓
3. train_cnn_model           # Conv2D → MaxPool → Dense
   ↓
4. evaluate_accuracy         # Test set 평가 (accuracy, loss)
   ↓
5. log_to_mlflow            # MLflow 로깅
   ↓
6. register_model           # Model Registry 등록
```

#### 📈 Tick 데이터 DAG
```
Tasks:
1. load_tick_from_database   # PostgreSQL/Iceberg 테이블
   ↓
2. feature_engineering       # 이동평균, RSI, MACD, Bollinger Bands
   ↓
3. create_sequences          # 시계열 윈도우 생성 (60 timesteps)
   ↓
4. split_train_test         # 시계열 분할 (순서 유지)
   ↓
5. train_lstm_model         # LSTM/GRU 학습
   ↓
6. evaluate_metrics         # MSE, MAE, RMSE
   ↓
7. log_to_mlflow           # MLflow 로깅
   ↓
8. register_model          # Model Registry 등록
```

**차이점**:
| 항목 | MNIST | Tick 데이터 |
|------|-------|------------|
| **Task 수** | 6개 | 8개 |
| **데이터 소스** | Keras 다운로드 | 데이터베이스 쿼리 |
| **전처리** | 이미지 정규화 | 시계열 피처 엔지니어링 |
| **모델** | CNN | LSTM/GRU |
| **평가 메트릭** | Accuracy | MSE/MAE |

→ **Task 구성이 완전히 다르므로 하나의 DAG로 통합하면 복잡하고 유지보수 어려움**

---

### 4️⃣ Airflow UI 모니터링 편리성

#### ✅ 개별 DAG 방식 (권장)
```
Airflow UI 대시보드:
┌─────────────────────────────────────────────────┐
│ DAG 목록                                        │
├─────────────────────────────────────────────────┤
│ 📊 mnist_cnn_training        [성공] ✅          │
│    마지막 실행: 2시간 전                         │
│    다음 실행: 5일 후                             │
├─────────────────────────────────────────────────┤
│ 📊 cifar10_training          [성공] ✅          │
│    마지막 실행: 3시간 전                         │
│    다음 실행: 4일 후                             │
├─────────────────────────────────────────────────┤
│ 📊 tick_data_training        [실패] ❌          │  ← 한눈에 파악!
│    마지막 실행: 10분 전                          │
│    오류: Database connection timeout             │
│    다음 실행: 23시간 후                          │
├─────────────────────────────────────────────────┤
│ 📊 household_power_training  [성공] ✅          │
│    마지막 실행: 5분 전                           │
│    다음 실행: 23시간 후                          │
└─────────────────────────────────────────────────┘
```

#### ❌ 단일 DAG 방식 (비권장)
```
Airflow UI:
┌─────────────────────────────────────────────────┐
│ 📊 all_models_training       [실패] ❌          │
│    마지막 실행: 10분 전                          │
│    ↓ Task 목록 열어야 어떤 모델이 실패했는지 확인 가능
│    ├─ mnist_task ✅
│    ├─ cifar10_task ✅
│    ├─ tick_task ❌  ← 찾기 어려움
│    └─ power_task ⏸️ (실행 안됨)
└─────────────────────────────────────────────────┘
```

---

### 5️⃣ 스케줄링 유연성

각 모델은 **다른 실행 주기**가 필요합니다:

```python
# mnist_cnn_dag.py
dag = DAG(
    'mnist_cnn_training',
    schedule=timedelta(days=7),  # 주 1회
    ...
)

# tick_data_dag.py
dag = DAG(
    'tick_data_training',
    schedule=timedelta(days=1),  # 매일
    ...
)
```

**단일 DAG로는 불가능**:
- ❌ 모든 모델이 같은 주기로 실행됨
- ❌ MNIST는 매일 불필요하게 재학습
- ❌ Tick 데이터는 주 1회로는 부족

---

## 🏗️ 권장 아키텍처

### 디렉토리 구조

```
dags/
├── common/                          # 공통 유틸리티 라이브러리
│   ├── __init__.py
│   ├── data_loader.py              # 데이터 로드 함수
│   │   └── DataLoader.load_mnist()
│   │   └── DataLoader.load_cifar10()
│   │   └── DataLoader.load_tick_data()
│   │   └── DataLoader.load_household_power()
│   │
│   ├── mlflow_utils.py             # MLflow 로깅 및 추적
│   │   └── MLflowTracker.log_params()
│   │   └── MLflowTracker.log_metrics()
│   │   └── MLflowTracker.log_model_pickle()
│   │   └── MLflowTracker.register_model()
│   │
│   ├── validation.py               # 모델 검증
│   │   └── ModelValidator.classification_metrics()
│   │   └── ModelValidator.regression_metrics()
│   │
│   └── preprocessing.py            # 전처리 유틸리티
│       └── TimeSeriesPreprocessor.create_sequences()
│       └── TimeSeriesPreprocessor.add_time_features()
│
├── models/                          # 모델 정의 및 학습 코드
│   ├── __init__.py
│   ├── mnist_cnn.py                # MNIST CNN 모델 + 학습 함수
│   ├── cifar10_cnn.py              # CIFAR-10 CNN 모델 + 학습 함수
│   ├── tick_data_models.py         # Tick LSTM/GRU 모델 + 학습 함수
│   └── household_power_lgb.py      # LightGBM 모델 + 학습 함수
│
├── configs/                         # 설정 파일 (Optional)
│   ├── mnist_config.py
│   ├── cifar10_config.py
│   ├── tick_data_config.py
│   └── household_power_config.py
│
├── ml_pipeline_dag.py              # 기존 (Lakehouse 통합 파이프라인)
│
├── mnist_cnn_dag.py                # NEW ⭐ MNIST CNN 학습 DAG
├── cifar10_dag.py                  # NEW ⭐ CIFAR-10 학습 DAG
├── tick_data_dag.py                # NEW ⭐ Tick 데이터 학습 DAG
└── household_power_dag.py          # NEW ⭐ 가정집 전력 학습 DAG
```

---

### 공통 라이브러리 역할

| 파일 | 역할 | 예시 |
|------|------|------|
| `common/data_loader.py` | 데이터 로드 | MNIST 다운로드, CSV 읽기, DB 쿼리 |
| `common/mlflow_utils.py` | MLflow 연동 | 파라미터/메트릭 로깅, 모델 등록 |
| `common/validation.py` | 모델 검증 | Accuracy, F1, MSE, RMSE 계산 |
| `common/preprocessing.py` | 전처리 | 시계열 윈도우 생성, 시간 피처 추가 |
| `models/*.py` | 모델 정의 | CNN 아키텍처, LSTM 아키텍처, 학습 함수 |

**핵심 원칙**:
- ✅ **DRY (Don't Repeat Yourself)**: 공통 로직은 한 곳에서 관리
- ✅ **재사용성**: 모든 DAG가 common 라이브러리 활용
- ✅ **유지보수성**: 버그 수정이나 개선 시 한 곳만 변경

---

## 📊 설계 옵션 비교

### 옵션 A: 단일 DAG (❌ 비권장)

```python
# all_models_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

dag = DAG('all_models_training', schedule=timedelta(days=1), ...)

mnist_task = PythonOperator(task_id='mnist', python_callable=train_mnist, dag=dag)
cifar10_task = PythonOperator(task_id='cifar10', python_callable=train_cifar10, dag=dag)
tick_task = PythonOperator(task_id='tick', python_callable=train_tick, dag=dag)
power_task = PythonOperator(task_id='power', python_callable=train_power, dag=dag)

# 순차 실행
mnist_task >> cifar10_task >> tick_task >> power_task
```

**문제점**:
| 문제 | 설명 | 심각도 |
|------|------|--------|
| **오류 전파** | 한 Task 실패 시 다음 Task 실행 안됨 | ⭐⭐⭐⭐⭐ |
| **스케줄링 통일** | 모든 모델이 같은 주기로 실행 | ⭐⭐⭐⭐⭐ |
| **재실행 어려움** | 특정 모델만 재실행 불가 | ⭐⭐⭐⭐ |
| **로그 찾기** | 어떤 모델 실패했는지 Task 목록 확인 필요 | ⭐⭐⭐ |
| **모니터링** | DAG 레벨에서 전체 상태만 확인 가능 | ⭐⭐⭐ |

---

### 옵션 B: 개별 DAG + 공통 라이브러리 (✅ 권장)

```python
# mnist_cnn_dag.py
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from common.data_loader import DataLoader
from common.mlflow_utils import MLflowTracker
from models.mnist_cnn import train_mnist_cnn

default_args = {
    'owner': 'airflow',
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'mnist_cnn_training',
    default_args=default_args,
    description='MNIST CNN Model Training',
    schedule=timedelta(days=7),      # 주 1회
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['ml', 'cnn', 'mnist'],
)

load_data_task = PythonOperator(
    task_id='load_mnist_data',
    python_callable=DataLoader.load_mnist,
    dag=dag,
)

train_task = PythonOperator(
    task_id='train_cnn',
    python_callable=train_mnist_cnn,
    dag=dag,
)

load_data_task >> train_task
```

**장점**:
| 장점 | 설명 | 중요도 |
|------|------|--------|
| **독립 실행** | 각 DAG가 완전히 독립적으로 실행 | ⭐⭐⭐⭐⭐ |
| **오류 격리** | 한 DAG 실패가 다른 DAG에 영향 없음 | ⭐⭐⭐⭐⭐ |
| **개별 스케줄링** | 각 DAG마다 다른 실행 주기 설정 가능 | ⭐⭐⭐⭐⭐ |
| **코드 재사용** | common 라이브러리로 중복 제거 | ⭐⭐⭐⭐ |
| **유지보수** | 각 DAG는 자기 로직만 관리 | ⭐⭐⭐⭐ |
| **모니터링** | Airflow UI에서 각 모델 상태 한눈에 파악 | ⭐⭐⭐⭐ |
| **테스트** | 각 DAG 독립 테스트 가능 | ⭐⭐⭐⭐ |
| **확장성** | 새 모델 추가 시 새 DAG 파일만 추가 | ⭐⭐⭐⭐ |

---

## 🔑 핵심 정리

### "각각의 DAG 파일을 만들어야 하는가?"

**답: 예, 각 모델마다 별도의 DAG 파일을 만들어야 합니다.**

### 이유 요약

| # | 이유 | 설명 | 중요도 |
|---|------|------|--------|
| 1 | **독립 실행** | 한 모델 오류가 다른 모델에 영향 안줌 | ⭐⭐⭐⭐⭐ |
| 2 | **개별 스케줄링** | MNIST 주1회, Tick 매일 → 다른 주기 필요 | ⭐⭐⭐⭐⭐ |
| 3 | **오류 격리** | Tick DAG 실패해도 Power DAG는 정상 실행 | ⭐⭐⭐⭐⭐ |
| 4 | **유지보수** | 각 DAG는 자기 로직만 관리, 코드 명확 | ⭐⭐⭐⭐ |
| 5 | **모니터링** | Airflow UI에서 각 모델 상태 한눈에 파악 | ⭐⭐⭐⭐ |
| 6 | **테스트** | 각 DAG 독립 테스트 가능 | ⭐⭐⭐⭐ |
| 7 | **확장성** | 5번째, 6번째 모델 추가 시 쉽게 확장 | ⭐⭐⭐⭐ |

---

## 🚀 구현 예시

### 1️⃣ MNIST CNN DAG (`mnist_cnn_dag.py`)

```python
"""
MNIST CNN Model Training DAG

목적: 손글씨 숫자(0-9) 분류 CNN 모델 학습
스케줄: 주 1회
데이터: tensorflow.keras.datasets.mnist
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from common.data_loader import DataLoader
from common.mlflow_utils import MLflowTracker
from common.validation import ModelValidator
from models.mnist_cnn import create_mnist_cnn, train_mnist_cnn

# MLflow 설정
MLFLOW_TRACKING_URI = 'http://mlflow:5000'

# DAG 기본 설정
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

# DAG 정의
dag = DAG(
    'mnist_cnn_training',
    default_args=default_args,
    description='MNIST CNN Model Training',
    schedule=timedelta(days=7),           # 주 1회
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['ml', 'cnn', 'mnist', 'image-classification'],
)


# Task 1: 데이터 로드
def load_data(**context):
    """MNIST 데이터 다운로드 및 전처리"""
    (X_train, y_train), (X_test, y_test) = DataLoader.load_mnist()

    # XCom에 데이터 크기 전달
    context['task_instance'].xcom_push(key='train_samples', value=len(X_train))
    context['task_instance'].xcom_push(key='test_samples', value=len(X_test))

    print(f"✅ MNIST 데이터 로드 완료: Train={len(X_train)}, Test={len(X_test)}")


# Task 2: 모델 학습
def train_model(**context):
    """CNN 모델 학습 및 평가"""
    # 데이터 로드
    (X_train, y_train), (X_test, y_test) = DataLoader.load_mnist()

    # MLflow 초기화
    tracker = MLflowTracker(MLFLOW_TRACKING_URI, 'mnist_cnn')

    # 모델 학습
    history, model = train_mnist_cnn(X_train, y_train, X_test, y_test, tracker)

    # 평가
    y_pred = model.predict(X_test).argmax(axis=1)
    metrics = ModelValidator.classification_metrics(y_test, y_pred)

    # MLflow 로깅
    tracker.log_metrics(metrics)
    tracker.log_model_pickle(model, 'mnist_cnn_model')

    print(f"✅ 모델 학습 완료: Accuracy={metrics['accuracy']:.4f}")

    # XCom에 결과 전달
    context['task_instance'].xcom_push(key='accuracy', value=metrics['accuracy'])


# Tasks 정의
load_data_task = PythonOperator(
    task_id='load_mnist_data',
    python_callable=load_data,
    dag=dag,
)

train_model_task = PythonOperator(
    task_id='train_cnn_model',
    python_callable=train_model,
    dag=dag,
)

# Task 의존성
load_data_task >> train_model_task
```

---

### 2️⃣ Tick 데이터 DAG (`tick_data_dag.py`)

```python
"""
Tick Data Model Training DAG

목적: 금융 Tick 데이터 시계열 예측 (LSTM)
스케줄: 매일
데이터: PostgreSQL/Iceberg 테이블
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from common.data_loader import DataLoader
from common.mlflow_utils import MLflowTracker
from common.validation import ModelValidator
from common.preprocessing import TimeSeriesPreprocessor
from models.tick_data_models import create_lstm_model, train_tick_lstm

# 설정
MLFLOW_TRACKING_URI = 'http://mlflow:5000'
TICK_DATA_PATH = '/data/tick/latest.csv'  # 또는 DB 연결

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'tick_data_training',
    default_args=default_args,
    description='Tick Data LSTM Model Training',
    schedule=timedelta(days=1),           # 매일
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['ml', 'lstm', 'timeseries', 'finance'],
)


def load_tick_data(**context):
    """Tick 데이터 로드"""
    df = DataLoader.load_tick_data(TICK_DATA_PATH)
    print(f"✅ Tick 데이터 로드 완료: {len(df)} rows")
    context['task_instance'].xcom_push(key='data_rows', value=len(df))


def feature_engineering(**context):
    """시계열 피처 엔지니어링"""
    df = DataLoader.load_tick_data(TICK_DATA_PATH)

    # 기술적 지표 추가
    df['MA_20'] = df['close'].rolling(window=20).mean()
    df['MA_50'] = df['close'].rolling(window=50).mean()
    # ... RSI, MACD 등 추가

    print(f"✅ 피처 엔지니어링 완료: {len(df.columns)} features")


def create_sequences_task(**context):
    """시계열 윈도우 생성"""
    df = DataLoader.load_tick_data(TICK_DATA_PATH)

    # 윈도우 슬라이싱
    X, y = TimeSeriesPreprocessor.create_sequences(df.values, seq_length=60)

    print(f"✅ 시퀀스 생성 완료: X={X.shape}, y={y.shape}")
    context['task_instance'].xcom_push(key='sequence_count', value=len(X))


def train_lstm(**context):
    """LSTM 모델 학습"""
    # 데이터 준비 (실제로는 이전 Task에서 전달받음)
    df = DataLoader.load_tick_data(TICK_DATA_PATH)
    X, y = TimeSeriesPreprocessor.create_sequences(df.values, seq_length=60)

    # Train/Test 분할
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # MLflow 초기화
    tracker = MLflowTracker(MLFLOW_TRACKING_URI, 'tick_data_lstm')

    # 모델 학습
    model = train_tick_lstm(X_train, y_train, X_test, y_test, tracker)

    # 평가
    y_pred = model.predict(X_test)
    metrics = ModelValidator.regression_metrics(y_test, y_pred)

    # MLflow 로깅
    tracker.log_metrics(metrics)
    tracker.log_model_pickle(model, 'tick_lstm_model')

    print(f"✅ LSTM 학습 완료: MSE={metrics['mse']:.4f}, RMSE={metrics['rmse']:.4f}")


# Tasks 정의
load_task = PythonOperator(task_id='load_tick_data', python_callable=load_tick_data, dag=dag)
feature_task = PythonOperator(task_id='feature_engineering', python_callable=feature_engineering, dag=dag)
sequence_task = PythonOperator(task_id='create_sequences', python_callable=create_sequences_task, dag=dag)
train_task = PythonOperator(task_id='train_lstm', python_callable=train_lstm, dag=dag)

# Task 의존성
load_task >> feature_task >> sequence_task >> train_task
```

---

## ❓ 자주 묻는 질문 (FAQ)

### Q1: "코드가 중복되지 않나요?"

**A**: 공통 라이브러리(`common/`)로 해결합니다.

```python
# 모든 DAG에서 재사용
from common.data_loader import DataLoader
from common.mlflow_utils import MLflowTracker
from common.validation import ModelValidator
```

---

### Q2: "DAG 파일이 너무 많아지지 않나요?"

**A**: 4개의 DAG 파일은 적절한 수준입니다.

- ✅ 각 DAG가 명확한 목적을 가짐
- ✅ 10개 이상이면 팩토리 패턴 고려
- ✅ 현재 4개는 관리 가능한 수준

---

### Q3: "새로운 모델 추가 시 어떻게 하나요?"

**A**: 새 DAG 파일만 추가하면 됩니다.

```python
# 5번째 모델: ImageNet 분류
# imagenet_dag.py

from common.data_loader import DataLoader  # 기존 라이브러리 재사용
from common.mlflow_utils import MLflowTracker
...
```

---

### Q4: "모든 DAG를 한번에 실행할 수 있나요?"

**A**: Airflow UI에서 가능합니다.

1. **수동 트리거**: 각 DAG 개별 트리거
2. **외부 트리거**: `TriggerDagRunOperator` 사용
3. **CLI**: `airflow dags trigger <dag_id>`

---

## 📋 다음 단계

### 구현 전 확인 필요 사항

| # | 질문 | 옵션 | 추천 |
|---|------|------|------|
| 1 | **Tick 데이터 소스는?** | 로컬 CSV / Iceberg 테이블 / 실시간 스트림 | 로컬 CSV (간단) |
| 2 | **전력 데이터 소스는?** | 로컬 CSV / UCI Repository / 데이터베이스 | 로컬 CSV (간단) |
| 3 | **스케줄링 정책은?** | MNIST/CIFAR 주1회? Tick/전력 매일? | MNIST/CIFAR 주1회, Tick/전력 매일 |
| 4 | **모델 복잡도는?** | 간단 (프로토타입) / 하이퍼파라미터 튜닝 포함 | 간단 버전으로 시작 |

---

### 제안하는 구현 순서

#### Phase 1: 공통 라이브러리 구축 (1일)
```
✅ dags/common/__init__.py
✅ dags/common/data_loader.py
✅ dags/common/mlflow_utils.py
✅ dags/common/validation.py
```

#### Phase 2: 간단한 모델부터 시작 (2-3일)
```
✅ dags/mnist_cnn_dag.py        (가장 간단)
✅ dags/cifar10_dag.py          (MNIST와 유사)
```

#### Phase 3: 복잡한 모델 추가 (3-4일)
```
✅ dags/tick_data_dag.py        (시계열 처리)
✅ dags/household_power_dag.py  (LightGBM + 피처 엔지니어링)
```

---

## 🎯 최종 결론

### "각각의 DAG 파일을 만들어야 해?"

**답: 네, 반드시 각 모델마다 별도의 DAG 파일을 만들어야 합니다.** ✅

### 핵심 이유 3가지

1. **독립 실행**: 한 모델 오류가 다른 모델에 영향 없음
2. **개별 스케줄링**: MNIST 주1회, Tick 매일 → 다른 주기 필요
3. **유지보수**: 각 DAG는 자기 로직만 관리, 코드 명확

### 권장 구조

```
dags/
├── common/              (공통 라이브러리)
├── models/              (모델 정의)
├── mnist_cnn_dag.py     ⭐
├── cifar10_dag.py       ⭐
├── tick_data_dag.py     ⭐
└── household_power_dag.py ⭐
```

---

**준비되셨으면 바로 구현을 시작하겠습니다!** 🚀

---

**문서 끝**

*작성일: 2025-12-27*
*작성자: Claude Sonnet 4.5*
*버전: 1.0*
