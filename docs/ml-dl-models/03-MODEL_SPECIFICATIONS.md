# ML/DL 모델 상세 사양

## 📋 목차

1. [XGBoost 사양](#xgboost-사양)
2. [LightGBM 사양](#lightgbm-사양)
3. [TensorFlow/Keras 사양](#tensorflowkeras-사양)
4. [PyTorch 사양](#pytorch-사양)
5. [성능 비교](#성능-비교)

---

## XGBoost 사양

### 라이브러리 정보

- **버전**: 2.0.3 이상
- **공식 문서**: https://xgboost.readthedocs.io/
- **GitHub**: https://github.com/dmlc/xgboost

### 기본 파라미터

| 파라미터 | 설명 | 추천값 |
|---------|------|-------|
| `max_depth` | 트리 최대 깊이 | 6 |
| `eta` (learning_rate) | 학습률 | 0.3 |
| `objective` | 손실 함수 | binary:logistic (이진) / multi:softmax (다중) |
| `num_boost_round` | 부스팅 라운드 | 100 |
| `subsample` | 샘플링 비율 | 0.8 |
| `colsample_bytree` | 피처 샘플링 비율 | 0.8 |

### 모델 구조

```python
import xgboost as xgb
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# 데이터 준비
X, y = make_classification(n_samples=10000, n_features=20, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# DMatrix 생성
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

# 파라미터 설정
params = {
    'max_depth': 6,
    'eta': 0.3,
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'subsample': 0.8,
    'colsample_bytree': 0.8,
}

# 모델 학습
model = xgb.train(
    params,
    dtrain,
    num_boost_round=100,
    evals=[(dtrain, 'train'), (dtest, 'test')],
    early_stopping_rounds=10,
    verbose_eval=10
)

# 예측
predictions = model.predict(dtest)
```

### 예상 성능

- **학습 시간**: 2GB 데이터 기준 ~ 30초
- **메모리 사용**: 입력 데이터 크기의 약 2-3배
- **정확도**: 튜닝 시 85-95%

### MLflow 통합

```python
import mlflow
import mlflow.xgboost

mlflow.xgboost.autolog()

with mlflow.start_run():
    # 모델 학습
    model = xgb.train(params, dtrain, num_boost_round=100)
    # 자동으로 파라미터, 메트릭, 모델이 로깅됨
```

---

## LightGBM 사양

### 라이브러리 정보

- **버전**: 4.1.0 이상
- **공식 문서**: https://lightgbm.readthedocs.io/
- **GitHub**: https://github.com/microsoft/LightGBM

### 기본 파라미터

| 파라미터 | 설명 | 추천값 |
|---------|------|-------|
| `num_leaves` | 리프 노드 수 | 31 |
| `learning_rate` | 학습률 | 0.05 |
| `objective` | 손실 함수 | binary / multiclass |
| `num_boost_round` | 부스팅 라운드 | 100 |
| `subsample` | 샘플링 비율 | 0.8 |
| `feature_fraction` | 피처 샘플링 비율 | 0.8 |

### 모델 구조

```python
import lightgbm as lgb
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

# 데이터 준비
X, y = make_classification(n_samples=10000, n_features=20, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Dataset 생성
dtrain = lgb.Dataset(X_train, label=y_train)
dtest = lgb.Dataset(X_test, label=y_test, reference=dtrain)

# 파라미터 설정
params = {
    'num_leaves': 31,
    'learning_rate': 0.05,
    'objective': 'binary',
    'metric': 'binary_logloss',
    'subsample': 0.8,
    'feature_fraction': 0.8,
}

# 모델 학습
model = lgb.train(
    params,
    dtrain,
    num_boost_round=100,
    valid_sets=[dtest],
    early_stopping_rounds=10,
    verbose_eval=10
)

# 예측
predictions = model.predict(X_test)
```

### 예상 성능

- **학습 시간**: 2GB 데이터 기준 ~ 15초 (XGBoost 대비 2배 빠름)
- **메모리 사용**: XGBoost 대비 20-30% 적음
- **정확도**: XGBoost와 동등 또는 약간 높음

### MLflow 통합

```python
import mlflow
import mlflow.lightgbm

mlflow.lightgbm.autolog()

with mlflow.start_run():
    # 모델 학습
    model = lgb.train(params, dtrain, num_boost_round=100)
    # 자동으로 파라미터, 메트릭, 모델이 로깅됨
```

---

## TensorFlow/Keras 사양

### 라이브러리 정보

- **TensorFlow 버전**: 2.15.0 이상
- **Keras 버전**: 3.0.0 이상
- **공식 문서**: https://tensorflow.org/
- **GitHub**: https://github.com/tensorflow/tensorflow

### MNIST MLP 사양

**아키텍처**:
```
Input (784) → Dense (128, relu) → Dropout (0.2) → Dense (10, softmax)
```

**파라미터 수**: ~100K

**코드 예제**:
```python
import tensorflow as tf
from tensorflow import keras

# 모델 정의
model = keras.Sequential([
    keras.layers.Flatten(input_shape=(28, 28)),
    keras.layers.Dense(128, activation='relu'),
    keras.layers.Dropout(0.2),
    keras.layers.Dense(10, activation='softmax')
])

# 컴파일
model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# 학습
history = model.fit(
    x_train, y_train,
    epochs=10,
    batch_size=128,
    validation_split=0.1,
    verbose=1
)

# 평가
test_loss, test_acc = model.evaluate(x_test, y_test)
```

**예상 성능**:
- 학습 시간: CPU 기준 5-10분 (10 epochs)
- 정확도: ~97%
- 메모리: 약 2-3GB

### MNIST CNN 사양

**아키텍처**:
```
Input (28, 28, 1)
→ Conv2D (32, 3×3, relu) → MaxPool (2×2)
→ Conv2D (64, 3×3, relu) → MaxPool (2×2)
→ Flatten
→ Dense (64, relu)
→ Dense (10, softmax)
```

**파라미터 수**: ~100K

**코드 예제**:
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

model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

history = model.fit(
    x_train.reshape(-1, 28, 28, 1), y_train,
    epochs=10,
    batch_size=128,
    validation_split=0.1,
    verbose=1
)
```

**예상 성능**:
- 학습 시간: CPU 기준 20-30분 (10 epochs)
- 정확도: ~99%
- 메모리: 약 3-4GB

### MLflow 통합

```python
import mlflow
import mlflow.tensorflow

mlflow.tensorflow.autolog()

with mlflow.start_run():
    # 모델 학습
    history = model.fit(x_train, y_train, epochs=10)
    # 자동으로 파라미터, 메트릭이 로깅됨
```

---

## PyTorch 사양

### 라이브러리 정보

- **PyTorch 버전**: 2.1.0 이상
- **TorchVision 버전**: 0.16.0 이상
- **공식 문서**: https://pytorch.org/
- **GitHub**: https://github.com/pytorch/pytorch

### MNIST MLP 사양

**아키텍처**:
```python
class MLP(nn.Module):
    Input (784) → Linear (128) → ReLU → Dropout (0.2) → Linear (10)
```

**파라미터 수**: ~100K

**코드 예제**:
```python
import torch
import torch.nn as nn
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

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

# 모델, 손실함수, 옵티마이저
model = MLP()
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters())

# 학습
for epoch in range(10):
    for images, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

# 평가
correct = 0
total = 0
with torch.no_grad():
    for images, labels in test_loader:
        outputs = model(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

accuracy = 100 * correct / total
```

**예상 성능**:
- 학습 시간: CPU 기준 5-10분
- 정확도: ~97%
- 메모리: 약 2-3GB

### MNIST CNN 사양

**아키텍처**:
```python
class CNN(nn.Module):
    Input (1, 28, 28)
    → Conv2D (32, 3×3) → ReLU → MaxPool (2×2)
    → Conv2D (64, 3×3) → ReLU → MaxPool (2×2)
    → Flatten
    → Linear (64*5*5, 64) → ReLU
    → Linear (64, 10)
```

**파라미터 수**: ~100K

**코드 예제**:
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

**예상 성능**:
- 학습 시간: CPU 기준 20-30분
- 정확도: ~99%
- 메모리: 약 3-4GB

### MLflow 통합

```python
import mlflow
import mlflow.pytorch

mlflow.pytorch.autolog()

with mlflow.start_run():
    # 모델 학습
    for epoch in range(10):
        # 학습 코드
        pass
    # 자동으로 메트릭이 로깅됨
```

---

## 성능 비교

### 학습 시간 비교 (CPU 기준)

| 모델 | 학습 시간 | 상대값 |
|------|----------|-------|
| XGBoost (2GB 데이터) | ~30초 | 1x |
| LightGBM (2GB 데이터) | ~15초 | 0.5x |
| TensorFlow MLP (10 epochs) | 5-10분 | 10-20x |
| TensorFlow CNN (10 epochs) | 20-30분 | 40-60x |
| PyTorch MLP (10 epochs) | 5-10분 | 10-20x |
| PyTorch CNN (10 epochs) | 20-30분 | 40-60x |

### 정확도 비교

| 모델 | MNIST 정확도 | 설명 |
|------|-----------|------|
| XGBoost | ~85% | Tabular 데이터용 (MNIST에는 부최적) |
| LightGBM | ~87% | Tabular 데이터용 (MNIST에는 부최적) |
| TensorFlow MLP | ~97% | 기본 MLP |
| TensorFlow CNN | ~99% | CNN (이미지에 최적화) |
| PyTorch MLP | ~97% | 기본 MLP |
| PyTorch CNN | ~99% | CNN (이미지에 최적화) |

### 메모리 사용량

| 모델 | 메모리 사용 |
|------|-----------|
| XGBoost | 데이터 크기의 2-3배 |
| LightGBM | 데이터 크기의 1.5-2배 |
| TensorFlow MLP | 2-3GB |
| TensorFlow CNN | 3-4GB |
| PyTorch MLP | 2-3GB |
| PyTorch CNN | 3-4GB |

---

**다음**: [Airflow DAG 예제 읽기 →](04-AIRFLOW_DAG_EXAMPLES.md)
