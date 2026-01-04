"""
Evaluate MNIST CNN with PyTorch (script)
=======================================

이 스크립트는 "단독 실행"과 "Airflow에서 호출" 모두를 위해 작성되었습니다.

- 학습된 state_dict 파일을 로드하여 MNIST 테스트셋으로 평가(evaluate)합니다.
- 실행 후 마지막 줄에 JSON 결과를 출력합니다(상위 DAG가 파싱하여 MLflow 로깅 등에 사용).

인자/환경변수(선택, 인자가 우선):
- MNIST_DATA_DIR       (default: /tmp/mnist-data)
- MNIST_MODEL_PATH     (required for Airflow; default: /tmp/mnist_cnn_model.pth)
- MNIST_TEST_SAMPLES   (default: 1000)
- MNIST_RUN_ID_PATH    (default: empty)
- MLFLOW_EXPERIMENT_NAME (default: mnist-cnn)
- MLFLOW_RUN_NAME        (default: mnist_cnn_eval)
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
    from torch.utils.data import DataLoader, Subset
    from torchvision import datasets, transforms

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("MNIST_DATA_DIR", "/tmp/mnist-data"))
    parser.add_argument("--model-path", default=os.getenv("MNIST_MODEL_PATH", "/tmp/mnist_cnn_model.pth"))
    parser.add_argument("--test-samples", type=int, default=_get_int("MNIST_TEST_SAMPLES", 1000))
    parser.add_argument("--run-id-path", default=os.getenv("MNIST_RUN_ID_PATH", ""))
    parser.add_argument("--mlflow-experiment", default=os.getenv("MLFLOW_EXPERIMENT_NAME", "mnist-cnn"))
    parser.add_argument("--mlflow-run-name", default=os.getenv("MLFLOW_RUN_NAME", "mnist_cnn_eval"))
    args = parser.parse_args()

    data_root = args.data_dir
    model_path = args.model_path
    test_samples = args.test_samples
    run_id_path = args.run_id_path.strip()
    mlflow_experiment = args.mlflow_experiment
    mlflow_run_name = args.mlflow_run_name

    torch.manual_seed(42)
    start = time.time()

    transform = transforms.Compose([transforms.ToTensor()])
    full_test = datasets.MNIST(root=data_root, train=False, download=True, transform=transform)
    test_subset = Subset(full_test, list(range(min(test_samples, len(full_test)))))
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
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    criterion = nn.CrossEntropyLoss()
    num_classes = 10
    cm = [[0 for _ in range(num_classes)] for _ in range(num_classes)]
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
            for true_label, pred_label in zip(labels, preds):
                cm[int(true_label.item())][int(pred_label.item())] += 1

    test_accuracy = correct / total if total else 0.0
    test_loss = test_loss_sum / total if total else 0.0

    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    mlflow_enabled = bool(mlflow_tracking_uri)
    mlflow = None
    if mlflow_enabled:
        try:
            import mlflow  # type: ignore[no-redef]
        except ModuleNotFoundError:
            mlflow_enabled = False

    run_id = None
    if run_id_path and os.path.exists(run_id_path):
        with open(run_id_path, "r", encoding="utf-8") as run_file:
            run_id = run_file.read().strip() or None

    if mlflow_enabled and mlflow_tracking_uri:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        active_run = None
        if run_id:
            try:
                active_run = mlflow.start_run(run_id=run_id)
            except Exception:
                mlflow.set_experiment(mlflow_experiment)
                active_run = mlflow.start_run(run_name=mlflow_run_name)
        else:
            mlflow.set_experiment(mlflow_experiment)
            active_run = mlflow.start_run(run_name=mlflow_run_name)

        if active_run is not None:
            run_id = active_run.info.run_id

        mlflow.log_param("framework", "pytorch")
        mlflow.log_param("stage", "evaluate")
        mlflow.log_param("model_path", model_path)
        mlflow.log_param("test_samples", int(len(test_subset)))
        mlflow.log_metric("test_accuracy", float(test_accuracy))
        mlflow.log_metric("test_loss", float(test_loss))
        mlflow.log_metric("eval_duration_sec", float(time.time() - start))

        cm_path = os.path.join(os.path.dirname(model_path) or ".", "confusion_matrix.png")
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(6, 6))
            im = ax.imshow([[int(value) for value in row] for row in cm], cmap="Blues")
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            ax.set_xlabel("Predicted")
            ax.set_ylabel("True")
            ax.set_title("MNIST Confusion Matrix")
            fig.tight_layout()
            fig.savefig(cm_path)
            plt.close(fig)
            try:
                mlflow.log_artifact(cm_path, artifact_path="eval")
            except Exception as exc:
                print(f"MLflow artifact logging failed: {exc}")
        except Exception:
            cm_txt_path = os.path.join(os.path.dirname(model_path) or ".", "confusion_matrix.csv")
            with open(cm_txt_path, "w", encoding="utf-8") as cm_file:
                for row in cm:
                    cm_file.write(",".join(str(value) for value in row))
                    cm_file.write("\n")
            try:
                mlflow.log_artifact(cm_txt_path, artifact_path="eval")
            except Exception as exc:
                print(f"MLflow artifact logging failed: {exc}")

        mlflow.end_run()

    result = {
        "framework": "pytorch",
        "stage": "evaluate",
        "model_path": model_path,
        "test_samples": int(len(test_subset)),
        "test_accuracy": float(test_accuracy),
        "test_loss": float(test_loss),
        "run_id": run_id,
        "duration_sec": float(time.time() - start),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
