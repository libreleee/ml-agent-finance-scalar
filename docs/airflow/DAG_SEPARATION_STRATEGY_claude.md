# Airflow DAG 분리 전략 - Claude 제안

**작성일**: 2025-12-27
**작성자**: Claude AI Assistant
**목적**: 4가지 모델(MNIST CNN, CIFAR-10, Tick 데이터, 가정집 전력) 학습을 위한 DAG 구조 설계

---

## 📋 목차

1. [현재 상황 분석](#1-현재-상황-분석)
2. [설계 옵션 비교](#2-설계-옵션-비교)
3. [권장 설계 (옵션 3)](#3-권장-설계-옵션-3)
4. [디렉토리 구조](#4-디렉토리-구조)
5. [각 DAG 상세 구성](#5-각-dag-상세-구성)
6. [공통 라이브러리 설계](#6-공통-라이브러리-설계)
7. [구현 단계](#7-구현-단계)
8. [추가 논의 사항](#8-추가-논의-사항)

---

## 1. 현재 상황 분석

### 1.1 기존 DAG 구조

```
dags/
└── ml_pipeline_dag.py  (Lakehouse 통합 파이프라인)
    ├── raw_to_bronze
    ├── bronze_to_silver
    ├── silver_to_gold
    ├── feature_engineering
    ├── model_training (RandomForest)
    ├── model_evaluation
    └── model_registry
```

**특징**:
- End-to-End Lakehouse 데이터 파이프라인
- Bronze → Silver → Gold 아키텍처
- MLflow 연동
- 7개 Task로 구성

### 1.2 새로운 요구사항

4가지 새로운 모델 학습 파이프라인 추가:

| # | 데이터셋 | 모델 | 목적 |
|---|---------|------|------|
| 1 | **MNIST** | CNN | 손글씨 숫자 분류 |
| 2 | **CIFAR-10** | CNN | 이미지 분류 (10개 클래스) |
| 3 | **Tick 데이터** | 시계열 모델 | 금융 틱 데이터 예측 |
| 4 | **가정집 전력** | LightGBM | 전력 소비량 예측 |

---

## 2. 설계 옵션 비교

### 옵션 1: 개별 DAG 파일 생성

```
dags/
├── ml_pipeline_dag.py           (기존)
├── mnist_cnn_dag.py             (NEW)
├── cifar10_dag.py               (NEW)
├── tick_data_dag.py             (NEW)
└── household_power_dag.py       (NEW)
```

#### 장점
- ✅ **독립성**: 각 모델이 독립적으로 실행/관리
- ✅ **명확성**: 파이프라인 구조가 명확
- ✅ **디버깅**: 테스트/디버깅 용이
- ✅ **재사용**: 태스크 그룹화 및 재사용 가능

#### 단점
- ❌ **코드 중복**: 데이터 로드, 전처리, 모델 평가 로직 중복
- ❌ **유지보수**: 공통 로직 변경 시 여러 파일 수정 필요

---

### 옵션 2: 팩토리 패턴 + 단일 파일

```python
# dags/model_training_dag_factory.py
def create_model_training_dag(dataset_name, model_type, config):
    dag = DAG(
        dag_id=f'{dataset_name}_{model_type}_training',
        default_args=default_args,
        ...
    )

    # 동적으로 Task 생성
    load_task = create_data_loader_task(dataset_name)
    train_task = create_training_task(model_type)
    ...

    return dag

# DAG 인스턴스 생성
mnist_dag = create_model_training_dag('mnist', 'cnn', mnist_config)
cifar10_dag = create_model_training_dag('cifar10', 'cnn', cifar10_config)
tick_dag = create_model_training_dag('tick', 'timeseries', tick_config)
power_dag = create_model_training_dag('household_power', 'lightgbm', power_config)
```

#### 장점
- ✅ **재사용성**: 코드 재사용 극대화
- ✅ **유지보수**: 공통 로직 한 곳에서 관리
- ✅ **확장성**: 새로운 모델 추가 시 설정만 추가
- ✅ **일관성**: 모든 DAG가 동일한 패턴 따름

#### 단점
- ❌ **복잡도**: 초기 설계 복잡
- ❌ **특수성**: 각 모델의 특이한 요구사항 반영 어려움
- ❌ **가독성**: 동적 생성으로 인한 가독성 저하

---

### 옵션 3: 공통 라이브러리 + 개별 DAG ⭐ **추천**

```
dags/
├── common/
│   ├── __init__.py
│   ├── data_loader.py          (공통 데이터 로드)
│   ├── mlflow_utils.py         (MLflow 로깅)
│   └── validation.py           (모델 검증)
├── models/
│   ├── __init__.py
│   ├── mnist_cnn.py
│   ├── cifar10_cnn.py
│   ├── tick_data_models.py
│   └── household_power_lgb.py
├── ml_pipeline_dag.py          (기존)
├── mnist_cnn_dag.py            (NEW - 공통 라이브러리 활용)
├── cifar10_dag.py              (NEW)
├── tick_data_dag.py            (NEW)
└── household_power_dag.py      (NEW)
```

#### 장점
- ✅ **균형**: 코드 재사용 + 독립성 확보
- ✅ **커스터마이징**: 각 DAG별 특수 로직 구현 가능
- ✅ **유지보수**: 공통 로직 변경 시 common 디렉토리만 수정
- ✅ **확장성**: 새 모델 추가 시 common 라이브러리 활용
- ✅ **테스트**: 각 DAG 독립 테스트 + 공통 유틸 단위 테스트

#### 단점
- ❌ **초기 작업**: 공통 라이브러리 설계 필요
- ❌ **복잡도**: 중간 수준의 초기 설정

---

## 3. 권장 설계 (옵션 3)

### 3.1 선택 이유

| 기준 | 옵션 1 | 옵션 2 | 옵션 3 ⭐ |
|------|--------|--------|----------|
| **코드 재사용** | ❌ 낮음 | ✅ 높음 | ✅ 높음 |
| **독립성** | ✅ 높음 | ❌ 낮음 | ✅ 높음 |
| **커스터마이징** | ✅ 쉬움 | ❌ 어려움 | ✅ 쉬움 |
| **확장성** | ⚠️ 보통 | ✅ 높음 | ✅ 높음 |
| **유지보수** | ❌ 어려움 | ✅ 쉬움 | ✅ 쉬움 |
| **초기 복잡도** | ✅ 낮음 | ❌ 높음 | ⚠️ 보통 |
| **가독성** | ✅ 높음 | ❌ 낮음 | ✅ 높음 |
| **테스트** | ✅ 쉬움 | ⚠️ 보통 | ✅ 쉬움 |

**결론**: 옵션 3이 **균형잡힌 최적의 솔루션**

### 3.2 핵심 원칙

1. **DRY (Don't Repeat Yourself)**: 공통 로직은 `common/` 디렉토리에
2. **SRP (Single Responsibility)**: 각 DAG는 하나의 모델에만 집중
3. **모듈화**: 모델 정의는 `models/` 디렉토리에 분리
4. **재사용성**: 공통 유틸리티로 코드 재사용 극대화
5. **독립성**: 각 DAG는 독립적으로 실행/테스트 가능

---

## 4. 디렉토리 구조

### 4.1 전체 구조

```
dags/
├── common/                          ← 공통 유틸리티 라이브러리
│   ├── __init__.py
│   ├── data_loader.py              (데이터 로드 함수들)
│   ├── model_trainer.py            (모델 학습 공통 로직)
│   ├── mlflow_utils.py             (MLflow 로깅 및 추적)
│   ├── validation.py               (모델 검증 함수들)
│   └── preprocessing.py            (전처리 유틸리티)
│
├── models/                          ← 모델 정의 및 학습 코드
│   ├── __init__.py
│   ├── mnist_cnn.py                (MNIST CNN 모델)
│   ├── cifar10_cnn.py              (CIFAR-10 CNN 모델)
│   ├── tick_data_models.py         (Tick 데이터 시계열 모델)
│   └── household_power_lgb.py      (LightGBM 모델)
│
├── configs/                         ← DAG 설정 파일 (Optional)
│   ├── mnist_config.py
│   ├── cifar10_config.py
│   ├── tick_data_config.py
│   └── household_power_config.py
│
├── ml_pipeline_dag.py              (기존: Lakehouse 통합 파이프라인)
├── mnist_cnn_dag.py                (NEW: MNIST CNN DAG)
├── cifar10_dag.py                  (NEW: CIFAR-10 DAG)
├── tick_data_dag.py                (NEW: Tick 데이터 DAG)
└── household_power_dag.py          (NEW: 가정집 전력 DAG)
```

### 4.2 파일 역할

| 디렉토리/파일 | 역할 | 예시 |
|--------------|------|------|
| `common/data_loader.py` | 데이터 로드 | MNIST 다운로드, CSV 읽기 |
| `common/mlflow_utils.py` | MLflow 연동 | 파라미터/메트릭 로깅, 모델 등록 |
| `common/validation.py` | 모델 검증 | Accuracy, F1, MSE 계산 |
| `models/mnist_cnn.py` | 모델 정의 | CNN 아키텍처, 학습 함수 |
| `configs/mnist_config.py` | 설정 | 배치 크기, 에포크, 하이퍼파라미터 |
| `mnist_cnn_dag.py` | DAG 정의 | Task 정의 및 의존성 |

---

## 5. 각 DAG 상세 구성

### 5.1 공통 Task 구조

모든 DAG는 다음 공통 흐름을 따름:

```
1. 데이터 로드 (load_data)
   ↓
2. 데이터 전처리 (preprocess_data)
   ↓
3. 모델 학습 (train_model)
   ↓
4. 모델 평가 (evaluate_model)
   ↓
5. MLflow 로깅 (log_to_mlflow)
   ↓
6. 모델 레지스트리 등록 (register_model)
```

### 5.2 각 DAG별 상세 구성

#### 1️⃣ MNIST CNN DAG (`mnist_cnn_dag.py`)

**목적**: 손글씨 숫자(0-9) 분류 CNN 모델 학습

**Tasks**:
```python
download_mnist_data       # Keras에서 MNIST 다운로드
  ↓
normalize_images         # 이미지 정규화 (0-1)
  ↓
train_cnn_model          # CNN 모델 학습 (Conv2D → MaxPool → Dense)
  ↓
evaluate_model           # Test set 평가 (Accuracy, Loss)
  ↓
log_to_mlflow           # MLflow에 메트릭/파라미터 기록
  ↓
register_model          # MLflow Model Registry 등록
```

**특수성**:
- 데이터 소스: `tensorflow.keras.datasets.mnist`
- 이미지 크기: 28×28 grayscale
- 클래스 수: 10
- 모델: Simple CNN (Conv → Pool → Flatten → Dense)

---

#### 2️⃣ CIFAR-10 DAG (`cifar10_dag.py`)

**목적**: 10개 클래스 이미지 분류 (비행기, 자동차, 새 등)

**Tasks**:
```python
load_cifar10_data        # Keras에서 CIFAR-10 다운로드
  ↓
augment_images          # 데이터 증강 (회전, 플립, 크롭)
  ↓
train_cnn_model         # CNN 또는 전이학습 모델 (ResNet, VGG)
  ↓
evaluate_model          # Test set 평가
  ↓
log_to_mlflow          # MLflow 로깅
  ↓
register_model         # 모델 등록
```

**특수성**:
- 데이터 소스: `tensorflow.keras.datasets.cifar10`
- 이미지 크기: 32×32 RGB
- 클래스 수: 10
- 모델: ResNet 또는 커스텀 CNN
- 데이터 증강: `ImageDataGenerator` 사용

---

#### 3️⃣ Tick 데이터 DAG (`tick_data_dag.py`)

**목적**: 금융 Tick 데이터 시계열 예측

**Tasks**:
```python
load_tick_data           # CSV/Parquet에서 Tick 데이터 로드
  ↓
feature_engineering     # 시계열 피처 생성
                        # - 이동평균 (MA)
                        # - 볼린저 밴드
                        # - RSI, MACD
  ↓
create_sequences        # 윈도우 슬라이싱 (예: 60 timesteps)
  ↓
train_timeseries_model  # LSTM/GRU/Transformer 모델
  ↓
evaluate_model         # MSE, MAE, RMSE
  ↓
log_to_mlflow         # MLflow 로깅
  ↓
register_model        # 모델 등록
```

**특수성**:
- 데이터 소스: `/data/tick/*.csv` 또는 Iceberg 테이블
- 시계열 길이: 가변 (예: 1,000,000 ticks)
- 피처: Open, High, Low, Close, Volume + 파생 피처
- 모델: LSTM, GRU, 또는 Temporal Fusion Transformer
- 윈도우 크기: 60 timesteps

---

#### 4️⃣ 가정집 전력 DAG (`household_power_dag.py`)

**목적**: 가정 전력 소비량 예측 (LightGBM)

**Tasks**:
```python
load_power_data          # CSV/Parquet에서 전력 데이터 로드
  ↓
feature_engineering     # 시간 기반 피처 생성
                        # - 시간대 (아침/점심/저녁/밤)
                        # - 요일 (주중/주말)
                        # - 계절 (봄/여름/가을/겨울)
                        # - 이동평균
  ↓
train_lightgbm_model   # LightGBM 학습
  ↓
hyperparameter_tuning  # Optuna로 하이퍼파라미터 튜닝
  ↓
evaluate_model        # MAE, RMSE, R²
  ↓
log_to_mlflow        # MLflow 로깅
  ↓
register_model       # 모델 등록
```

**특수성**:
- 데이터 소스: `/data/household_power/*.csv` 또는 데이터베이스
- 주기: 분 단위 or 시간 단위
- 타겟: 전력 소비량 (kW)
- 모델: LightGBM (회귀)
- 하이퍼파라미터 튜닝: Optuna 또는 GridSearch

---

## 6. 공통 라이브러리 설계

### 6.1 `common/data_loader.py`

```python
"""
공통 데이터 로드 함수들
"""
import numpy as np
import pandas as pd
from tensorflow.keras.datasets import mnist, cifar10


class DataLoader:
    """데이터 로드 유틸리티"""

    @staticmethod
    def load_mnist():
        """MNIST 데이터 로드 및 정규화"""
        (X_train, y_train), (X_test, y_test) = mnist.load_data()

        # 정규화
        X_train = X_train.astype('float32') / 255.0
        X_test = X_test.astype('float32') / 255.0

        # 차원 추가 (28, 28) → (28, 28, 1)
        X_train = np.expand_dims(X_train, axis=-1)
        X_test = np.expand_dims(X_test, axis=-1)

        return (X_train, y_train), (X_test, y_test)

    @staticmethod
    def load_cifar10():
        """CIFAR-10 데이터 로드 및 정규화"""
        (X_train, y_train), (X_test, y_test) = cifar10.load_data()

        # 정규화
        X_train = X_train.astype('float32') / 255.0
        X_test = X_test.astype('float32') / 255.0

        return (X_train, y_train), (X_test, y_test)

    @staticmethod
    def load_tick_data(file_path: str, columns: list = None):
        """Tick 데이터 로드"""
        df = pd.read_csv(file_path)

        if columns:
            df = df[columns]

        # 시간 인덱스 설정
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

        return df

    @staticmethod
    def load_household_power(file_path: str):
        """가정집 전력 데이터 로드"""
        df = pd.read_csv(file_path, sep=';', parse_dates=['datetime'])

        # 결측치 처리
        df.replace('?', np.nan, inplace=True)
        df.dropna(inplace=True)

        # 숫자형 변환
        numeric_cols = ['Global_active_power', 'Global_reactive_power',
                       'Voltage', 'Global_intensity']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col])

        return df
```

---

### 6.2 `common/mlflow_utils.py`

```python
"""
MLflow 유틸리티 함수
"""
import mlflow
import mlflow.keras
import mlflow.lightgbm
import pickle
import os


class MLflowTracker:
    """MLflow 추적 및 로깅"""

    def __init__(self, tracking_uri: str, experiment_name: str):
        """
        Args:
            tracking_uri: MLflow 서버 URI
            experiment_name: 실험 이름
        """
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)

    def log_params(self, params: dict):
        """파라미터 로깅"""
        for key, value in params.items():
            mlflow.log_param(key, value)

    def log_metrics(self, metrics: dict):
        """메트릭 로깅"""
        for key, value in metrics.items():
            mlflow.log_metric(key, value)

    def log_model_pickle(self, model, model_name: str):
        """
        Pickle로 모델 저장 (Task 5 버그 수정 적용)

        Args:
            model: 학습된 모델
            model_name: 모델 이름
        """
        model_path = f"/tmp/{model_name}.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        mlflow.log_artifact(model_path, artifact_path="model")

        return model_path

    def log_keras_model(self, model, model_name: str):
        """
        Keras 모델 저장

        Args:
            model: Keras 모델
            model_name: 모델 이름
        """
        # Keras 네이티브 저장 (권장)
        model_path = f"/tmp/{model_name}.h5"
        model.save(model_path)
        mlflow.log_artifact(model_path, artifact_path="model")

    def register_model(self, model_uri: str, model_name: str, stage: str = "Production"):
        """
        MLflow Model Registry에 모델 등록

        Args:
            model_uri: 모델 URI (예: runs:/<run_id>/model)
            model_name: 등록할 모델 이름
            stage: 모델 스테이지 (Staging, Production)
        """
        from mlflow.tracking import MlflowClient

        client = MlflowClient()

        try:
            # 모델 등록
            model_version = mlflow.register_model(model_uri, model_name)

            # 스테이지 전환
            client.transition_model_version_stage(
                name=model_name,
                version=model_version.version,
                stage=stage
            )

            print(f"✅ 모델 등록 완료: {model_name} v{model_version.version} ({stage})")

            return model_version

        except Exception as e:
            print(f"⚠️ 모델 등록 실패: {e}")
            return None
```

---

### 6.3 `common/validation.py`

```python
"""
모델 검증 유틸리티
"""
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score
)
import numpy as np


class ModelValidator:
    """모델 평가"""

    @staticmethod
    def classification_metrics(y_true, y_pred):
        """
        분류 모델 평가 메트릭

        Returns:
            dict: {accuracy, precision, recall, f1}
        """
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='weighted'),
            'recall': recall_score(y_true, y_pred, average='weighted'),
            'f1_score': f1_score(y_true, y_pred, average='weighted')
        }

    @staticmethod
    def regression_metrics(y_true, y_pred):
        """
        회귀 모델 평가 메트릭

        Returns:
            dict: {mse, rmse, mae, r2}
        """
        mse = mean_squared_error(y_true, y_pred)

        return {
            'mse': mse,
            'rmse': np.sqrt(mse),
            'mae': mean_absolute_error(y_true, y_pred),
            'r2': r2_score(y_true, y_pred)
        }
```

---

### 6.4 `common/preprocessing.py`

```python
"""
데이터 전처리 유틸리티
"""
import numpy as np
import pandas as pd


class TimeSeriesPreprocessor:
    """시계열 데이터 전처리"""

    @staticmethod
    def create_sequences(data, seq_length: int):
        """
        시계열 윈도우 슬라이싱

        Args:
            data: 입력 데이터 (numpy array 또는 DataFrame)
            seq_length: 윈도우 크기

        Returns:
            X, y: (samples, seq_length, features), (samples,)
        """
        X, y = [], []

        for i in range(len(data) - seq_length):
            X.append(data[i:i+seq_length])
            y.append(data[i+seq_length])

        return np.array(X), np.array(y)

    @staticmethod
    def add_time_features(df: pd.DataFrame, timestamp_col: str = 'timestamp'):
        """
        시간 기반 피처 추가

        Args:
            df: 입력 DataFrame
            timestamp_col: 타임스탬프 컬럼명

        Returns:
            DataFrame with time features
        """
        df = df.copy()

        df['hour'] = df[timestamp_col].dt.hour
        df['day_of_week'] = df[timestamp_col].dt.dayofweek
        df['month'] = df[timestamp_col].dt.month
        df['quarter'] = df[timestamp_col].dt.quarter

        # 시간대 구분
        df['time_of_day'] = pd.cut(
            df['hour'],
            bins=[0, 6, 12, 18, 24],
            labels=['night', 'morning', 'afternoon', 'evening']
        )

        # 주중/주말
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

        return df
```

---

## 7. 구현 단계

### Phase 1: 공통 라이브러리 구축 (1-2일)

1. **디렉토리 생성**
   ```bash
   mkdir -p dags/common dags/models dags/configs
   ```

2. **공통 유틸리티 작성**
   - `common/__init__.py`
   - `common/data_loader.py`
   - `common/mlflow_utils.py`
   - `common/validation.py`
   - `common/preprocessing.py`

3. **단위 테스트 작성**
   ```python
   # tests/test_data_loader.py
   def test_load_mnist():
       (X_train, y_train), (X_test, y_test) = DataLoader.load_mnist()
       assert X_train.shape == (60000, 28, 28, 1)
   ```

---

### Phase 2: 모델 정의 (2-3일)

1. **MNIST CNN 모델** (`models/mnist_cnn.py`)
   ```python
   def create_mnist_cnn():
       model = Sequential([
           Conv2D(32, (3,3), activation='relu', input_shape=(28,28,1)),
           MaxPooling2D((2,2)),
           Conv2D(64, (3,3), activation='relu'),
           MaxPooling2D((2,2)),
           Flatten(),
           Dense(64, activation='relu'),
           Dense(10, activation='softmax')
       ])
       return model
   ```

2. **CIFAR-10 CNN 모델** (`models/cifar10_cnn.py`)
3. **Tick 데이터 LSTM 모델** (`models/tick_data_models.py`)
4. **LightGBM 모델** (`models/household_power_lgb.py`)

---

### Phase 3: DAG 작성 (3-4일)

각 DAG 파일 작성:

1. **MNIST DAG** (`mnist_cnn_dag.py`)
2. **CIFAR-10 DAG** (`cifar10_dag.py`)
3. **Tick 데이터 DAG** (`tick_data_dag.py`)
4. **가정집 전력 DAG** (`household_power_dag.py`)

**DAG 템플릿 예시**:
```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from common.data_loader import DataLoader
from common.mlflow_utils import MLflowTracker
from common.validation import ModelValidator
from models.mnist_cnn import create_mnist_cnn, train_mnist_cnn

default_args = {
    'owner': 'airflow',
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'mnist_cnn_training',
    default_args=default_args,
    description='MNIST CNN Model Training',
    schedule=timedelta(days=7),  # 주 1회
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['ml', 'cnn', 'mnist'],
)

# Task 정의...
```

---

### Phase 4: 테스트 및 검증 (2-3일)

1. **단위 테스트**
   - 각 공통 함수 테스트
   - 모델 생성/학습 테스트

2. **통합 테스트**
   - 각 DAG 개별 실행
   - MLflow 로깅 검증
   - 모델 레지스트리 확인

3. **성능 테스트**
   - 학습 시간 측정
   - 메모리 사용량 모니터링

---

## 8. 추가 논의 사항

### 8.1 데이터 소스 확인

| 데이터셋 | 소스 | 질문 |
|---------|------|------|
| **MNIST** | Keras 다운로드 | ✅ 확정 |
| **CIFAR-10** | Keras 다운로드 | ✅ 확정 |
| **Tick 데이터** | ? | ❓ 로컬 CSV? Iceberg 테이블? 실시간 스트림? |
| **가정집 전력** | ? | ❓ 로컬 CSV? 데이터베이스? UCI Repository? |

**필요한 정보**:
- Tick 데이터 파일 경로 또는 데이터베이스 연결 정보
- 전력 데이터 파일 경로 또는 소스

---

### 8.2 모델 복잡도 결정

| 모델 | 간단 버전 | 고급 버전 | 추천 |
|------|---------|---------|------|
| **MNIST CNN** | 2-layer CNN | ResNet-like | 간단 |
| **CIFAR-10** | Simple CNN | ResNet50 전이학습 | 고급 |
| **Tick 데이터** | LSTM | Transformer | 고급 |
| **전력 데이터** | LightGBM | LightGBM + Optuna 튜닝 | 고급 |

**질문**:
- 각 모델의 목표 성능은?
- 학습 시간 제약은?
- 하이퍼파라미터 튜닝 필요 여부?

---

### 8.3 스케줄링 정책

| DAG | 추천 스케줄 | 이유 |
|-----|-----------|------|
| **MNIST** | 주 1회 | 데이터 고정, 재학습 불필요 |
| **CIFAR-10** | 주 1회 | 데이터 고정, 재학습 불필요 |
| **Tick 데이터** | 일 1회 | 매일 새로운 틱 데이터 |
| **전력 데이터** | 일 1회 | 매일 새로운 전력 데이터 |

**질문**:
- 실시간 학습 필요 여부?
- 수동 트리거 vs 자동 스케줄링?

---

### 8.4 MLflow 모델 레지스트리 전략

**모델 네이밍 규칙**:
```
{dataset}_{model_type}_{version}

예시:
- mnist_cnn_v1
- cifar10_resnet50_v2
- tick_lstm_v3
- household_power_lightgbm_v1
```

**모델 스테이지**:
- `None`: 초기 등록
- `Staging`: 테스트 중
- `Production`: 프로덕션 배포
- `Archived`: 아카이브

**질문**:
- 모델 자동 승격 정책?
- A/B 테스트 필요 여부?

---

## 9. 예상 일정

| Phase | 작업 | 기간 | 담당 |
|-------|------|------|------|
| **Phase 1** | 공통 라이브러리 구축 | 1-2일 | 개발자 |
| **Phase 2** | 모델 정의 작성 | 2-3일 | 데이터 과학자 |
| **Phase 3** | DAG 작성 | 3-4일 | 개발자 |
| **Phase 4** | 테스트 및 검증 | 2-3일 | QA |
| **Total** | - | **8-12일** | - |

---

## 10. 다음 단계

### 선택지

**A. 옵션 3 확정, 바로 구현 시작**
- ✅ 공통 라이브러리 작성
- ✅ 4개 DAG 파일 생성
- ✅ 테스트

**B. 추가 논의 필요**
- ❓ 데이터 소스 확인 (Tick/Power)
- ❓ 모델 복잡도 결정
- ❓ 스케줄링 정책
- ❓ MLflow 전략

**C. 다른 설계 재검토**
- 옵션 1 또는 2 재고려

---

## 부록: 참고 자료

### A. 기존 코드 참고

- `dags/ml_pipeline_dag.py` - 기존 Lakehouse 파이프라인
- `docs/bugfix/airflow/Task5-ModelTraining-MLflowAPIVersionMismatch.md` - MLflow 버그 수정 사례

### B. 외부 참고 자료

- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [MLflow Documentation](https://mlflow.org/docs/latest/)
- [LightGBM Python API](https://lightgbm.readthedocs.io/)

---

**문서 끝**

*작성일: 2025-12-27*
*최종 수정: 2025-12-27*
