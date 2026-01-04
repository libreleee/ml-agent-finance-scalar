"""
Train MNIST CNN with PyTorch (script)
====================================

이 스크립트는 "단독 실행"과 "Airflow에서 호출" 모두를 위해 작성되었습니다.

- 실행 후 마지막 줄에 JSON 결과를 출력합니다(상위 DAG가 파싱하여 MLflow 로깅 등에 사용).
- 빠른 예제/스모크 테스트를 위해 기본값은 작은 샘플/1 epoch 입니다.
- 이 스크립트는 **학습(train)만** 수행하고, 평가는 별도 스크립트에서 수행합니다.

인자/환경변수(선택, 인자가 우선):
- MNIST_DATA_DIR       (default: /tmp/mnist-data)
- MNIST_TRAIN_SAMPLES  (default: 5000)
- MNIST_EPOCHS         (default: 1)
- MNIST_BATCH_SIZE     (default: 64)
- MNIST_MODEL_PATH     (default: /tmp/mnist_cnn_model.pth)
- MNIST_RUN_ID_PATH    (default: empty)
- MLFLOW_EXPERIMENT_NAME (default: mnist-cnn)
- MLFLOW_RUN_NAME        (default: mnist_cnn_train)
"""

from __future__ import annotations

import argparse
import json
import os
import time


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def main() -> None:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Subset
    from torchvision import datasets, transforms

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("MNIST_DATA_DIR", "/tmp/mnist-data"))
    parser.add_argument("--model-path", default=os.getenv("MNIST_MODEL_PATH", "/tmp/mnist_cnn_model.pth"))
    parser.add_argument("--train-samples", type=int, default=_get_int("MNIST_TRAIN_SAMPLES", 5000))
    parser.add_argument("--epochs", type=int, default=_get_int("MNIST_EPOCHS", 1))
    parser.add_argument("--batch-size", type=int, default=_get_int("MNIST_BATCH_SIZE", 64))
    parser.add_argument("--run-id-path", default=os.getenv("MNIST_RUN_ID_PATH", ""))
    parser.add_argument("--mlflow-experiment", default=os.getenv("MLFLOW_EXPERIMENT_NAME", "mnist-cnn"))
    parser.add_argument("--mlflow-run-name", default=os.getenv("MLFLOW_RUN_NAME", "mnist_cnn_train"))
    args = parser.parse_args()

    data_root = args.data_dir
    model_path = args.model_path
    train_samples = args.train_samples
    epochs = args.epochs
    batch_size = args.batch_size
    run_id_path = args.run_id_path.strip()
    mlflow_experiment = args.mlflow_experiment
    mlflow_run_name = args.mlflow_run_name

    torch.manual_seed(42)
    start = time.time()

    transform = transforms.Compose([transforms.ToTensor()])
    full_train = datasets.MNIST(root=data_root, train=True, download=True, transform=transform)

    train_subset = Subset(full_train, list(range(min(train_samples, len(full_train)))))

    train_loader = DataLoader(train_subset, batch_size=batch_size, shuffle=True, num_workers=0)

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

    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    run_id = None
    mlflow_enabled = bool(mlflow_tracking_uri)
    mlflow = None
    if mlflow_enabled:
        try:
            import mlflow  # type: ignore[no-redef]
        except ModuleNotFoundError:
            mlflow_enabled = False

    if mlflow_enabled and mlflow_tracking_uri:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(mlflow_experiment)
        with mlflow.start_run(run_name=mlflow_run_name) as run:
            run_id = run.info.run_id
            mlflow.log_param("framework", "pytorch")
            mlflow.log_param("stage", "train")
            mlflow.log_param("epochs", epochs)
            mlflow.log_param("train_samples", int(len(train_subset)))
            mlflow.log_param("batch_size", batch_size)
            mlflow.log_param("model_path", model_path)

            model.train()
            for epoch in range(epochs):
                epoch_loss = 0.0
                correct = 0
                total = 0
                for images, labels in train_loader:
                    images, labels = images.to(device), labels.to(device)
                    optimizer.zero_grad()
                    logits = model(images)
                    loss = criterion(logits, labels)
                    loss.backward()
                    optimizer.step()

                    epoch_loss += float(loss.item()) * images.size(0)
                    preds = torch.argmax(logits, dim=1)
                    correct += int((preds == labels).sum().item())
                    total += int(labels.size(0))

                avg_loss = epoch_loss / total if total else 0.0
                acc = correct / total if total else 0.0
                mlflow.log_metric("train_loss", avg_loss, step=epoch + 1)
                mlflow.log_metric("train_accuracy", acc, step=epoch + 1)

            os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
            torch.save(model.state_dict(), model_path)
            mlflow.log_metric("train_duration_sec", float(time.time() - start))
            try:
                mlflow.log_artifact(model_path, artifact_path="model")
            except Exception as exc:
                print(f"MLflow artifact logging failed: {exc}")
    else:
        model.train()
        for _ in range(epochs):
            for images, labels in train_loader:
                images, labels = images.to(device), labels.to(device)
                optimizer.zero_grad()
                logits = model(images)
                loss = criterion(logits, labels)
                loss.backward()
                optimizer.step()

        os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
        torch.save(model.state_dict(), model_path)

    if run_id and run_id_path:
        os.makedirs(os.path.dirname(run_id_path) or ".", exist_ok=True)
        with open(run_id_path, "w", encoding="utf-8") as run_file:
            run_file.write(run_id)

    result = {
        "framework": "pytorch",
        "stage": "train",
        "epochs": epochs,
        "train_samples": int(len(train_subset)),
        "batch_size": batch_size,
        "model_path": model_path,
        "run_id": run_id,
        "duration_sec": float(time.time() - start),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
