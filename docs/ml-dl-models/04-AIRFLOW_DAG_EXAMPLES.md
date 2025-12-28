# Airflow DAG 완전 예제

## 📋 목차

1. [XGBoost DAG](#xgboost-dag)
2. [LightGBM DAG](#lightgbm-dag)
3. [TensorFlow MNIST MLP DAG](#tensorflow-mnist-mlp-dag)
4. [PyTorch MNIST MLP DAG](#pytorch-mnist-mlp-dag)

---

## XGBoost DAG

파일명: `dags/xgboost_pipeline_dag.py`

```python
"""
XGBoost Classification Pipeline with MLflow
============================================

이 DAG는 XGBoost 분류 모델을 학습하고 MLflow에 등록합니다.
- 데이터: scikit-learn make_classification으로 생성
- 모델: XGBoost 이진 분류
- 추적: MLflow 통합
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
import os

# MLflow 설정
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')

# 기본 인자
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG 정의
dag = DAG(
    'xgboost_classification_pipeline',
    default_args=default_args,
    description='XGBoost Classification with MLflow',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['ml', 'xgboost', 'mlflow'],
)


def load_data(**context):
    """데이터 로드 및 전처리"""
    import mlflow
    from sklearn.datasets import make_classification
    from sklearn.model_selection import train_test_split

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with mlflow.start_run(run_name="load_data"):
        # 데이터 생성
        X, y = make_classification(
            n_samples=10000,
            n_features=20,
            n_informative=15,
            n_redundant=5,
            random_state=42
        )
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # 메타데이터 로깅
        mlflow.log_param("n_samples", 10000)
        mlflow.log_param("n_features", 20)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("test_size", len(X_test))

        print(f"✅ 데이터 로드 완료: Train={len(X_train)}, Test={len(X_test)}")

        return {
            'train_size': len(X_train),
            'test_size': len(X_test)
        }


def train_xgboost(**context):
    """XGBoost 모델 학습"""
    import mlflow
    import mlflow.xgboost
    import xgboost as xgb
    from sklearn.datasets import make_classification
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.xgboost.autolog()

    with mlflow.start_run(run_name="train_xgboost"):
        # 데이터 로드
        X, y = make_classification(
            n_samples=10000,
            n_features=20,
            n_informative=15,
            n_redundant=5,
            random_state=42
        )
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # DMatrix 생성
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dtest = xgb.DMatrix(X_test, label=y_test)

        # 하이퍼파라미터
        params = {
            'max_depth': 6,
            'eta': 0.3,
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'subsample': 0.8,
            'colsample_bytree': 0.8,
        }

        # 하이퍼파라미터 로깅
        for key, value in params.items():
            mlflow.log_param(key, value)

        # 학습
        evals = [(dtrain, 'train'), (dtest, 'test')]
        model = xgb.train(
            params,
            dtrain,
            num_boost_round=100,
            evals=evals,
            early_stopping_rounds=10,
            verbose_eval=False
        )

        # 평가
        y_pred_proba = model.predict(dtest)
        y_pred = (y_pred_proba > 0.5).astype(int)

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)

        # 메트릭 로깅
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)
        mlflow.log_metric("f1_score", f1)

        print(f"✅ XGBoost 학습 완료")
        print(f"   Accuracy: {accuracy:.4f}")
        print(f"   Precision: {precision:.4f}")
        print(f"   Recall: {recall:.4f}")
        print(f"   F1-Score: {f1:.4f}")

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        }


def register_model(**context):
    """MLflow 모델 레지스트리에 등록"""
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # 최신 run 가져오기
    experiment = mlflow.get_experiment_by_name("Default")
    if experiment is None:
        print("❌ Default experiment를 찾을 수 없습니다")
        return

    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    if runs.empty:
        print("❌ 실행 기록이 없습니다")
        return

    latest_run = runs.iloc[0]
    latest_run_id = latest_run['run_id']

    # 모델 등록
    model_name = "xgboost_classifier"
    model_uri = f"runs:/{latest_run_id}/model"

    try:
        mlflow.register_model(model_uri, model_name)
        print(f"✅ 모델 등록 완료: {model_name}")
    except Exception as e:
        print(f"⚠️ 모델 등록 실패: {str(e)}")
        print(f"   (모델이 이미 등록되었을 수 있습니다)")


# Task 정의
load_data_task = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    dag=dag,
)

train_task = PythonOperator(
    task_id='train_xgboost',
    python_callable=train_xgboost,
    dag=dag,
)

register_task = PythonOperator(
    task_id='register_model',
    python_callable=register_model,
    dag=dag,
)

# Task 의존성
load_data_task >> train_task >> register_task
```

---

## LightGBM DAG

파일명: `dags/lightgbm_pipeline_dag.py`

XGBoost DAG과 거의 동일하며, 주요 차이점은:

```python
def train_lightgbm(**context):
    """LightGBM 모델 학습"""
    import mlflow
    import mlflow.lightgbm
    import lightgbm as lgb
    from sklearn.datasets import make_classification
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.lightgbm.autolog()

    with mlflow.start_run(run_name="train_lightgbm"):
        # 데이터 로드
        X, y = make_classification(
            n_samples=10000,
            n_features=20,
            random_state=42
        )
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Dataset 생성
        dtrain = lgb.Dataset(X_train, label=y_train)
        dtest = lgb.Dataset(X_test, label=y_test, reference=dtrain)

        # 파라미터
        params = {
            'num_leaves': 31,
            'learning_rate': 0.05,
            'objective': 'binary',
            'metric': 'binary_logloss',
            'subsample': 0.8,
            'feature_fraction': 0.8,
        }

        # 학습
        model = lgb.train(
            params,
            dtrain,
            num_boost_round=100,
            valid_sets=[dtest],
            early_stopping_rounds=10,
            verbose_eval=False
        )

        # 평가
        y_pred_proba = model.predict(X_test)
        y_pred = (y_pred_proba > 0.5).astype(int)

        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)

        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("f1_score", f1)

        print(f"✅ LightGBM 학습 완료: Accuracy={accuracy:.4f}, F1={f1:.4f}")

        return {'accuracy': accuracy, 'f1_score': f1}
```

---

## TensorFlow MNIST MLP DAG

파일명: `dags/tensorflow_mnist_mlp_dag.py`

```python
"""
TensorFlow MNIST MLP Pipeline with MLflow
==========================================

이 DAG는 MNIST 데이터셋을 사용하여 간단한 MLP를 학습합니다.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
import os

MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

dag = DAG(
    'tensorflow_mnist_mlp_pipeline',
    default_args=default_args,
    description='TensorFlow MNIST MLP with MLflow',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['dl', 'tensorflow', 'mnist', 'mlp'],
)


def download_mnist(**context):
    """MNIST 데이터셋 다운로드"""
    import mlflow
    import tensorflow as tf

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with mlflow.start_run(run_name="download_mnist"):
        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

        mlflow.log_param("train_samples", len(x_train))
        mlflow.log_param("test_samples", len(x_test))

        print(f"✅ MNIST 다운로드 완료")
        print(f"   Train: {len(x_train)}, Test: {len(x_test)}")

        return {
            'train_samples': len(x_train),
            'test_samples': len(x_test)
        }


def train_mlp(**context):
    """MNIST MLP 모델 학습"""
    import mlflow
    import mlflow.tensorflow
    import tensorflow as tf
    import numpy as np

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.tensorflow.autolog()

    with mlflow.start_run(run_name="train_mnist_mlp"):
        # 데이터 로드
        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

        # 전처리
        x_train = x_train / 255.0
        x_test = x_test / 255.0

        # 모델 정의
        model = tf.keras.Sequential([
            tf.keras.layers.Flatten(input_shape=(28, 28)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(10, activation='softmax')
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
        test_loss, test_acc = model.evaluate(x_test, y_test, verbose=0)

        mlflow.log_metric("test_accuracy", test_acc)
        mlflow.log_metric("test_loss", test_loss)
        mlflow.log_metric("final_train_loss", history.history['loss'][-1])
        mlflow.log_metric("final_train_accuracy", history.history['accuracy'][-1])

        print(f"✅ MLP 학습 완료")
        print(f"   Test Accuracy: {test_acc:.4f}")
        print(f"   Test Loss: {test_loss:.4f}")

        return {
            'test_accuracy': float(test_acc),
            'test_loss': float(test_loss)
        }


# Task 정의
download_task = PythonOperator(
    task_id='download_mnist',
    python_callable=download_mnist,
    dag=dag,
)

train_task = PythonOperator(
    task_id='train_mlp',
    python_callable=train_mlp,
    dag=dag,
)

# Task 의존성
download_task >> train_task
```

---

## PyTorch MNIST MLP DAG

파일명: `dags/pytorch_mnist_mlp_dag.py`

```python
"""
PyTorch MNIST MLP Pipeline with MLflow
=======================================

이 DAG는 MNIST 데이터셋을 사용하여 PyTorch MLP를 학습합니다.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
import os

MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')

default_args = {
    'owner': 'airflow',
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

dag = DAG(
    'pytorch_mnist_mlp_pipeline',
    default_args=default_args,
    description='PyTorch MNIST MLP with MLflow',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2025, 12, 27),
    catchup=False,
    tags=['dl', 'pytorch', 'mnist', 'mlp'],
)


def train_pytorch_mlp(**context):
    """PyTorch MNIST MLP 모델 학습"""
    import mlflow
    import mlflow.pytorch
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torchvision import datasets, transforms
    from torch.utils.data import DataLoader

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.pytorch.autolog()

    with mlflow.start_run(run_name="train_pytorch_mlp"):
        # 하이퍼파라미터
        epochs = 10
        batch_size = 128
        learning_rate = 0.001

        mlflow.log_param("epochs", epochs)
        mlflow.log_param("batch_size", batch_size)
        mlflow.log_param("learning_rate", learning_rate)

        # 데이터 로드
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))
        ])

        train_dataset = datasets.MNIST('./data', train=True, download=True, transform=transform)
        test_dataset = datasets.MNIST('./data', train=False, download=True, transform=transform)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

        # 모델 정의
        class MLP(nn.Module):
            def __init__(self):
                super().__init__()
                self.flatten = nn.Flatten()
                self.fc1 = nn.Linear(28*28, 128)
                self.relu = nn.ReLU()
                self.dropout = nn.Dropout(0.2)
                self.fc2 = nn.Linear(128, 10)

            def forward(self, x):
                x = self.flatten(x)
                x = self.fc1(x)
                x = self.relu(x)
                x = self.dropout(x)
                x = self.fc2(x)
                return x

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = MLP().to(device)

        # 손실함수와 옵티마이저
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=learning_rate)

        # 학습
        for epoch in range(epochs):
            model.train()
            train_loss = 0.0

            for images, labels in train_loader:
                images, labels = images.to(device), labels.to(device)

                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()

            mlflow.log_metric("train_loss", train_loss / len(train_loader), step=epoch)

        # 평가
        model.eval()
        correct = 0
        total = 0

        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)

                outputs = model(images)
                _, predicted = torch.max(outputs.data, 1)

                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        test_accuracy = 100 * correct / total
        mlflow.log_metric("test_accuracy", test_accuracy)

        print(f"✅ PyTorch MLP 학습 완료")
        print(f"   Test Accuracy: {test_accuracy:.2f}%")

        return {'test_accuracy': test_accuracy}


# Task 정의
train_task = PythonOperator(
    task_id='train_pytorch_mlp',
    python_callable=train_pytorch_mlp,
    dag=dag,
)
```

---

## MLflow 통합 패턴

### Autologging 활성화

각 프레임워크 자동 로깅 설정:

```python
# XGBoost
import mlflow.xgboost
mlflow.xgboost.autolog()

# LightGBM
import mlflow.lightgbm
mlflow.lightgbm.autolog()

# TensorFlow
import mlflow.tensorflow
mlflow.tensorflow.autolog()

# PyTorch
import mlflow.pytorch
mlflow.pytorch.autolog()
```

### Manual Logging 패턴

```python
with mlflow.start_run(run_name="experiment_name"):
    # 파라미터 로깅
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_param("batch_size", 128)

    # 학습 코드
    for epoch in range(epochs):
        loss = train_step()
        mlflow.log_metric("train_loss", loss, step=epoch)

    # 최종 메트릭
    mlflow.log_metric("final_accuracy", accuracy)
```

---

**다음**: [실행 계획 읽기 →](05-EXECUTION_PLAN.md)
