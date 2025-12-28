"""
MNIST CNN Training DAG (CPU) - PyTorch native in Airflow Worker
==============================================================

이 DAG는 PyTorch/torchvision을 Airflow worker 환경에 직접 설치(pip/커스텀 이미지)한 뒤,
PythonOperator로 MNIST를 CPU로 짧게 학습하고 MLflow에 기록하는 예제입니다.

주의:
- Airflow 컨테이너에 torch, torchvision이 설치되어 있어야 합니다.
- 운영 환경에서는 의존성/리소스 격리를 위해 Docker/K8s 실행 방식을 권장합니다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

try:
    from airflow.providers.standard.operators.python import PythonOperator
except ModuleNotFoundError:
    from airflow.operators.python import PythonOperator


MLFLOW_EXPERIMENT_NAME = "mnist-cnn"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=30),
}


def train_mnist_torch_native():
    import os
    import time

    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Subset
    from torchvision import datasets, transforms

    torch.manual_seed(42)

    start = time.time()

    data_root = os.getenv("MNIST_DATA_DIR", "/tmp/mnist-data")
    transform = transforms.Compose([transforms.ToTensor()])

    full_train = datasets.MNIST(root=data_root, train=True, download=True, transform=transform)
    full_test = datasets.MNIST(root=data_root, train=False, download=True, transform=transform)

    # 빠른 CPU 스모크 테스트(짧게)
    train_subset = Subset(full_train, list(range(5000)))
    test_subset = Subset(full_test, list(range(1000)))

    train_loader = DataLoader(train_subset, batch_size=64, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_subset, batch_size=128, shuffle=False, num_workers=0)

    class SmallCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(1, 16, kernel_size=3)
            self.conv2 = nn.Conv2d(16, 32, kernel_size=3)
            self.pool = nn.MaxPool2d(2, 2)
            self.fc1 = nn.Linear(32 * 5 * 5, 64)
            self.fc2 = nn.Linear(64, 10)

        def forward(self, x):
            x = torch.relu(self.conv1(x))
            x = self.pool(x)
            x = torch.relu(self.conv2(x))
            x = self.pool(x)
            x = torch.flatten(x, 1)
            x = torch.relu(self.fc1(x))
            x = self.fc2(x)
            return x

    device = torch.device("cpu")
    model = SmallCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    model.train()
    for _epoch in range(1):  # 1 epoch
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

    model.eval()
    correct = 0
    total = 0
    test_loss_sum = 0.0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            loss = criterion(logits, labels)
            test_loss_sum += float(loss.item()) * images.size(0)
            preds = torch.argmax(logits, dim=1)
            correct += int((preds == labels).sum().item())
            total += int(labels.size(0))

    test_accuracy = correct / total if total else 0.0
    test_loss = test_loss_sum / total if total else 0.0

    return {
        "framework": "pytorch",
        "epochs": 1,
        "train_samples": int(len(train_subset)),
        "test_samples": int(len(test_subset)),
        "test_accuracy": float(test_accuracy),
        "test_loss": float(test_loss),
        "duration_sec": float(time.time() - start),
    }


def log_to_mlflow(**context):
    import os

    import mlflow

    ti = context["ti"]
    result = ti.xcom_pull(task_ids="train_mnist_torch_native")
    if not isinstance(result, dict):
        raise ValueError("Expected dict XCom result from 'train_mnist_torch_native'")

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run(run_name="mnist_cnn_pytorch_native_cpu_smoke"):
        for key in ("framework", "epochs", "train_samples", "test_samples"):
            if key in result:
                mlflow.log_param(key, result[key])
        for key in ("test_accuracy", "test_loss", "duration_sec"):
            if key in result:
                mlflow.log_metric(key, result[key])

    return result


with DAG(
    dag_id="mnist_cnn_training_pytorch_native",
    default_args=default_args,
    description="MNIST CNN training (PyTorch native) + MLflow logging",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mnist", "cnn", "pytorch", "mlflow", "native"],
) as dag:
    # ============================================================================
    # Task 1: Train MNIST CNN (PyTorch, native)
    # ============================================================================
    task_train = PythonOperator(
        task_id="train_mnist_torch_native",
        python_callable=train_mnist_torch_native,
    )

    # ============================================================================
    # Task 2: Log Metrics to MLflow
    # ============================================================================
    task_log = PythonOperator(
        task_id="log_to_mlflow",
        python_callable=log_to_mlflow,
    )

    # ============================================================================
    # DAG Dependencies
    # ============================================================================
    task_train >> task_log

