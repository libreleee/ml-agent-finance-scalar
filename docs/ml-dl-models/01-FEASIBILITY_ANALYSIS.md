# ML/DL 모델 통합 가능성 분석

## 📋 목차

1. [현재 인프라 상태](#현재-인프라-상태)
2. [XGBoost 가능성 평가](#xgboost-가능성-평가)
3. [LightGBM 가능성 평가](#lightgbm-가능성-평가)
4. [TensorFlow/Keras 가능성 평가](#tensorflowkeras-가능성-평가)
5. [PyTorch 가능성 평가](#pytorch-가능성-평가)
6. [인프라 요구사항](#인프라-요구사항)
7. [제약사항 및 위험요소](#제약사항-및-위험요소)
8. [결론](#결론)

---

## 현재 인프라 상태

### 기존 ML 스택

| 컴포넌트 | 현재 상태 | 버전 |
|---------|----------|------|
| scikit-learn | ✅ 설치됨 | 1.3.2 |
| MLflow | ✅ 설치됨 | 2.9.2 |
| Airflow | ✅ 실행 중 | 2.8.0 |
| XGBoost | ❌ 미설치 | - |
| LightGBM | ❌ 미설치 | - |
| TensorFlow | ❌ 미설치 | - |
| PyTorch | ❌ 미설치 | - |

### 실행 환경

- **Airflow Worker**: Python task 실행 가능 (CeleryExecutor)
- **Jupyter Lab**: spark-iceberg 컨테이너 (포트 8888)
- **MLflow**: 실험 추적 및 모델 레지스트리 (포트 5000)
- **S3 Storage**: SeaweedFS (모델 아티팩트 저장)
- **Data Lake**: Iceberg + Trino

### 기존 ML 파이프라인

참조: `/home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py`

- **모델**: RandomForestClassifier (scikit-learn)
- **파이프라인**: RAW → Bronze → Silver → Gold → Features → Train → Registry
- **MLflow 통합**: 완료 (파라미터, 메트릭, 모델 로깅)
- **실행 주기**: 일일 스케줄

---

## XGBoost 가능성 평가

### ✅ 가능 여부: **가능**

### 필요 작업

1. **라이브러리 추가**
   - `requirements-airflow.txt`에 `xgboost>=2.0.3` 추가

2. **리소스 요구사항**
   - CPU: 최소 2 cores (현재 Airflow worker: 2 CPU) ✅
   - Memory: 최소 2GB (현재 Airflow worker: 2GB) ✅
   - **결론**: 추가 리소스 불필요

3. **MLflow 통합**
   - MLflow는 XGBoost autologging 지원
   - `mlflow.xgboost.autolog()` 사용 가능

4. **데이터 파이프라인**
   - 기존 Iceberg 테이블 활용 가능
   - Trino 쿼리로 feature 추출

### 코드 예제

```python
import xgboost as xgb
import mlflow
import mlflow.xgboost

mlflow.xgboost.autolog()

with mlflow.start_run():
    dtrain = xgb.DMatrix(X_train, label=y_train)
    params = {
        'max_depth': 6,
        'eta': 0.3,
        'objective': 'binary:logistic',
        'eval_metric': 'logloss'
    }
    model = xgb.train(params, dtrain, num_boost_round=100)
```

### 예상 성능

- **학습 속도**: scikit-learn RandomForest 대비 2-3배 빠름
- **메모리**: 유사 또는 약간 적음
- **정확도**: 일반적으로 더 높음

---

## LightGBM 가능성 평가

### ✅ 가능 여부: **가능**

### 필요 작업

1. **라이브러리 추가**
   - `requirements-airflow.txt`에 `lightgbm>=4.1.0` 추가

2. **리소스 요구사항**
   - CPU: 최소 2 cores ✅
   - Memory: 최소 2GB ✅
   - **결론**: 추가 리소스 불필요

3. **MLflow 통합**
   - MLflow는 LightGBM autologging 지원
   - `mlflow.lightgbm.autolog()` 사용 가능

4. **특징**
   - XGBoost보다 일반적으로 더 빠름
   - 메모리 효율적
   - 범주형 피처 native 지원

### 코드 예제

```python
import lightgbm as lgb
import mlflow
import mlflow.lightgbm

mlflow.lightgbm.autolog()

with mlflow.start_run():
    dtrain = lgb.Dataset(X_train, label=y_train)
    params = {
        'num_leaves': 31,
        'learning_rate': 0.05,
        'objective': 'binary'
    }
    model = lgb.train(params, dtrain, num_boost_round=100)
```

### 예상 성능

- **학습 속도**: XGBoost 대비 1.5-2배 빠름
- **메모리**: XGBoost 대비 약간 적음
- **정확도**: 유사하거나 약간 더 높을 수 있음

---

## TensorFlow/Keras 가능성 평가

### ✅ 가능 여부: **가능**

### 필요 작업

1. **라이브러리 추가**
   ```
   tensorflow>=2.15.0,<2.16.0
   keras>=3.0.0
   ```

2. **리소스 요구사항**

   **MNIST MLP**:
   - CPU: 2-4 cores (현재: 2 CPU - 학습 가능하나 느릴 수 있음)
   - Memory: 4GB (현재: 2GB - **메모리 증가 필요**)
   - 학습 시간: CPU 기준 5-10분

   **MNIST CNN**:
   - CPU: 4+ cores (현재: 2 CPU - **증가 권장**)
   - Memory: 4-6GB (현재: 2GB - **메모리 증가 필요**)
   - 학습 시간: CPU 기준 20-30분

3. **Docker 설정 변경 필요**
   ```yaml
   airflow-worker:
     deploy:
       resources:
         limits:
           cpus: '4'
           memory: 6G
         reservations:
           cpus: '2'
           memory: 4G
   ```

4. **MLflow 통합**
   - MLflow는 TensorFlow/Keras autologging 지원
   - `mlflow.tensorflow.autolog()` 사용 가능

5. **MNIST 데이터셋**
   - `tensorflow.keras.datasets.mnist` 사용
   - 자동 다운로드 (약 11MB)

### 모델 아키텍처

**MNIST MLP**:
```python
from tensorflow import keras

model = keras.Sequential([
    keras.layers.Flatten(input_shape=(28, 28)),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dropout(0.2),
    keras.layers.Dense(10, activation='softmax')
])
# 파라미터 수: ~100K
```

**MNIST CNN**:
```python
model = keras.Sequential([
    keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    keras.layers.MaxPooling2D((2, 2)),
    keras.layers.Conv2D(64, (3, 3), activation='relu'),
    keras.layers.MaxPooling2D((2, 2)),
    keras.layers.Flatten(),
    keras.layers.Dense(64, activation='relu'),
    keras.layers.Dense(10, activation='softmax')
])
# 파라미터 수: ~100K
```

### 예상 성능 (CPU)

| 모델 | 학습 시간 | 정확도 | 메모리 |
|------|----------|-------|--------|
| MLP | 5-10분 | ~97% | 2-3GB |
| CNN | 20-30분 | ~99% | 3-4GB |

---

## PyTorch 가능성 평가

### ✅ 가능 여부: **가능**

### 필요 작업

1. **라이브러리 추가**
   ```
   torch>=2.1.0,<2.3.0
   torchvision>=0.16.0
   ```

2. **리소스 요구사항**
   - TensorFlow와 동일:
     - CPU: 2-4 cores (CNN은 4+ 권장)
     - Memory: 4-6GB

3. **Docker 설정 변경**
   - TensorFlow와 동일한 리소스 증가 필요

4. **MLflow 통합**
   - MLflow는 PyTorch autologging 지원
   - `mlflow.pytorch.autolog()` 사용 가능

5. **MNIST 데이터셋**
   - `torchvision.datasets.MNIST` 사용
   - 자동 다운로드 (약 11MB)

### 모델 아키텍처

**MNIST MLP**:
```python
import torch.nn as nn

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(28*28, 128)
        self.dropout = nn.Dropout(0.2)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.flatten(x)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x
```

**MNIST CNN**:
```python
class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, 3)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(32, 64, 3)
        self.fc1 = nn.Linear(64 * 5 * 5, 64)
        self.fc2 = nn.Linear(64, 10)

    def forward(self, x):
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = x.view(-1, 64 * 5 * 5)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x
```

### 예상 성능 (CPU)

- TensorFlow와 거의 동일

---

## 인프라 요구사항

### 현재 리소스

```yaml
airflow-worker:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

### 권장 리소스 (모든 모델 포함)

**최소 요구사항**:
```yaml
airflow-worker:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 6G
      reservations:
        cpus: '2'
        memory: 4G
```

**이상적 요구사항** (더 빠른 학습):
```yaml
airflow-worker:
  deploy:
    resources:
      limits:
        cpus: '8'
        memory: 8G
      reservations:
        cpus: '4'
        memory: 6G
```

### 디스크 공간

- 라이브러리: TensorFlow (~500MB) + PyTorch (~800MB) = **~1.3GB**
- MNIST 데이터: **~50MB** (압축 해제 포함)
- 모델 체크포인트: 모델당 **~10MB**
- **총**: **~2GB** 추가 필요

### GPU 지원 (선택사항)

현재 설정에는 GPU 없음. GPU 추가 시:
- NVIDIA Docker runtime 설정 필요
- `tensorflow-gpu` 또는 `torch` (CUDA 지원) 설치
- 학습 속도: 10-100배 향상

---

## 제약사항 및 위험요소

### 1. 메모리 제약

- **현재**: Airflow worker 2GB
- **DL 모델 필요**: 4-6GB
- **해결**: Docker 리소스 제한 증가

### 2. CPU 성능

- **현재**: 2 cores
- **DL 학습**: 느릴 수 있음 (20-30분/epoch)
- **해결**: CPU 증가 또는 epoch 수 감소

### 3. 라이브러리 크기

- TensorFlow + PyTorch = ~1.3GB
- Docker 이미지 크기 증가
- **해결**: 빌드 시간 증가 감수

### 4. 버전 호환성

- TensorFlow와 PyTorch는 numpy 버전 충돌 가능
- **해결**: 호환 가능한 버전 선택
  ```
  numpy>=1.23.0,<2.0.0
  tensorflow>=2.15.0
  torch>=2.1.0
  ```

### 5. MLflow 로깅

- DL 모델은 로그 데이터가 많음 (메트릭, 그래프, 체크포인트)
- **해결**: S3 artifact storage 활용 (이미 구성됨)

### 6. 학습 시간

- CPU 기반 학습은 시간 소요
- Airflow task timeout 설정 필요
- **해결**: DAG에서 `execution_timeout` 증가
  ```python
  task = PythonOperator(
      ...
      execution_timeout=timedelta(hours=2)
  )
  ```

---

## 결론

### 종합 평가

| 모델 | 가능 여부 | 난이도 | 리소스 증가 | 우선순위 |
|------|----------|-------|------------|---------|
| **XGBoost** | ✅ | 쉬움 | 불필요 | 1 (가장 높음) |
| **LightGBM** | ✅ | 쉬움 | 불필요 | 2 |
| **TF MNIST MLP** | ✅ | 중간 | 메모리 2→4GB | 3 |
| **TF MNIST CNN** | ✅ | 중간 | 메모리 2→6GB, CPU 2→4 | 4 |
| **PyTorch MLP** | ✅ | 중간 | 메모리 2→4GB | 5 |
| **PyTorch CNN** | ✅ | 중간 | 메모리 2→6GB, CPU 2→4 | 6 |

### 권장 사항

1. **1단계: Traditional ML (XGBoost, LightGBM)**
   - 리소스 증가 불필요
   - 빠른 구현 및 테스트 가능
   - MLflow 통합 검증

2. **2단계: Deep Learning (TensorFlow/PyTorch)**
   - Docker 리소스 증가 후 구현
   - MNIST MLP부터 시작 (더 간단함)
   - CNN은 마지막에 구현

3. **3단계: 최적화**
   - GPU 추가 고려 (선택사항)
   - 분산 학습 (선택사항)

### 최종 답변

**질문**: "지금 이 프로젝트에서 ML XGBoost, LightGBM, DL MNIST MLP, CNN 다 동작시킬 수 있지?"

**답변**:
✅ **가능합니다!**

- **XGBoost, LightGBM**: 현재 인프라로 즉시 가능
- **TensorFlow/PyTorch MNIST MLP, CNN**: Docker 리소스 증가 후 가능
  - 메모리: 2GB → 4-6GB
  - CPU: 2 cores → 4+ cores (권장)

모든 모델은 Airflow DAG로 자동화 가능하며, MLflow로 실험 추적 가능합니다.

---

**다음**: [구현 가이드 읽기 →](02-IMPLEMENTATION_GUIDE.md)
