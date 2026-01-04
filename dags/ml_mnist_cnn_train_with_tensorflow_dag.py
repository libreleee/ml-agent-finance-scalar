"""
MNIST CNN Training DAG - train_with_tensorflow (in Airflow worker)
==================================================================

이 DAG는 TensorFlow/Keras를 Airflow worker 환경에 직접 설치(pip/커스텀 이미지)한 뒤,
학습 스크립트(`dags/scripts/train_mnist_cnn_tf.py`)를 실행하여 MNIST를 CPU로 짧게 학습하고,
결과를 MLflow에 기록하는 예제입니다.

주의:
- Airflow 컨테이너에 `tensorflow`가 설치되어 있어야 합니다.
- 운영 환경에서는 `train_with_docker`(또는 K8s Pod 실행) 방식이 더 안전합니다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

try:
    from airflow.providers.standard.operators.bash import BashOperator
    from airflow.providers.standard.operators.python import PythonOperator
except ModuleNotFoundError:
    from airflow.operators.bash import BashOperator
    from airflow.operators.python import PythonOperator

import json
import os

MLFLOW_EXPERIMENT_NAME = "mnist-cnn"
MLFLOW_TRACKING_URI = "http://mlflow:5000"

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=30),
}


with DAG(
    dag_id="mnist_cnn_training_train_with_tensorflow",
    default_args=default_args,
    description="MNIST CNN training (TF/Keras in Airflow worker) + MLflow logging (separate task)",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mnist", "cnn", "tensorflow", "mlflow", "bash_operator", "python_operator"],
) as dag:
    # ============================================================================
    # Task 1: Train MNIST CNN (TensorFlow/Keras, python script)
    # ============================================================================
    model_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_tensorflow/{{ ts_nodash }}/model.keras"
    run_id_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_tensorflow/{{ ts_nodash }}/run_id.txt"
    metrics_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_tensorflow/{{ ts_nodash }}/train_metrics.json"
    train_curve_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_tensorflow/{{ ts_nodash }}/train_curve.png"
    confusion_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_tensorflow/{{ ts_nodash }}/confusion_matrix.png"
    confusion_csv_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_tensorflow/{{ ts_nodash }}/confusion_matrix.csv"
    task_train = BashOperator(
        task_id="train_mnist_tf_script",
        bash_command=(
            "python /opt/airflow/dags/scripts/train_mnist_cnn_tf.py "
            f"--model-path '{model_path}' --run-id-path '{run_id_path}' "
            f"--metrics-path '{metrics_path}'"
        ),
        env={
            "MLFLOW_TRACKING_URI": "",
            "MNIST_EPOCHS": "10",
            "MNIST_EARLY_STOPPING": "true",
            "MNIST_ES_PATIENCE": "2",
            "MNIST_ES_MIN_DELTA": "0.0005",
        },
        do_xcom_push=True,
    )

    # ============================================================================
    # Task 2: Evaluate MNIST CNN (TensorFlow/Keras, python script)
    # ============================================================================
    task_evaluate = BashOperator(
        task_id="evaluate_mnist_tf_script",
        bash_command=(
            "python /opt/airflow/dags/scripts/evaluate_mnist_cnn_tf.py "
            f"--model-path '{model_path}' --run-id-path '{run_id_path}' "
            f"--confusion-path '{confusion_path}' --confusion-csv-path '{confusion_csv_path}'"
        ),
        env={
            "MLFLOW_TRACKING_URI": "",
        },
        do_xcom_push=True,
    )

    def _log_to_mlflow(
        train_result_json: str,
        eval_result_json: str,
        metrics_path: str,
        model_path: str,
        train_curve_path: str,
        confusion_path: str,
        confusion_csv_path: str,
        experiment_name: str,
        run_name: str,
        tracking_uri: str,
    ) -> None:
        import mlflow
        import socket
        from urllib.parse import urlparse

        train_result = json.loads(train_result_json) if train_result_json else {}
        eval_result = json.loads(eval_result_json) if eval_result_json else {}

        def _artifact_store_available() -> bool:
            endpoint = (
                os.getenv("MLFLOW_S3_ENDPOINT_URL")
                or os.getenv("AWS_ENDPOINT_URL_S3")
                or os.getenv("AWS_ENDPOINT_URL")
            )
            if not endpoint:
                return True
            host = urlparse(endpoint).hostname
            if not host:
                return True
            try:
                socket.getaddrinfo(host, None)
                return True
            except OSError:
                return False

        def _safe_log_artifact(path: str, artifact_path: str) -> None:
            try:
                mlflow.log_artifact(path, artifact_path=artifact_path)
            except Exception as exc:
                print(f"MLflow artifact logging failed: {exc}")
                try:
                    mlflow.set_tag("artifact_upload_error", str(exc)[:250])
                except Exception:
                    pass

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name):
            mlflow.log_param("framework", "tensorflow")
            mlflow.log_param("run_mode", "separate_log_to_mlflow")

            for key in (
                "epochs",
                "train_samples",
                "batch_size",
                "model_path",
                "early_stopping",
                "early_stopping_patience",
                "early_stopping_min_delta",
            ):
                if key in train_result and train_result[key] is not None:
                    mlflow.log_param(key, train_result[key])
            if "test_samples" in eval_result and eval_result["test_samples"] is not None:
                mlflow.log_param("test_samples", eval_result["test_samples"])

            for key in ("train_duration_sec", "duration_sec"):
                if key in train_result and train_result[key] is not None:
                    mlflow.log_metric("train_duration_sec", float(train_result[key]))
                    break
            if "early_stopping_stopped_epoch" in train_result and train_result["early_stopping_stopped_epoch"] is not None:
                mlflow.log_metric("early_stopping_stopped_epoch", float(train_result["early_stopping_stopped_epoch"]))
            if "early_stopping_best" in train_result and train_result["early_stopping_best"] is not None:
                mlflow.log_metric("early_stopping_best", float(train_result["early_stopping_best"]))
            if "duration_sec" in eval_result and eval_result["duration_sec"] is not None:
                mlflow.log_metric("eval_duration_sec", float(eval_result["duration_sec"]))
            if "test_accuracy" in eval_result and eval_result["test_accuracy"] is not None:
                mlflow.log_metric("test_accuracy", float(eval_result["test_accuracy"]))
            if "test_loss" in eval_result and eval_result["test_loss"] is not None:
                mlflow.log_metric("test_loss", float(eval_result["test_loss"]))

            if metrics_path and os.path.exists(metrics_path):
                with open(metrics_path, "r", encoding="utf-8") as metrics_file:
                    metrics = json.load(metrics_file)
                for step in range(len(metrics.get("loss", []))):
                    mlflow.log_metric("train_loss", metrics["loss"][step], step=step + 1)
                    if "accuracy" in metrics:
                        mlflow.log_metric("train_accuracy", metrics["accuracy"][step], step=step + 1)
                    if "val_loss" in metrics:
                        mlflow.log_metric("val_loss", metrics["val_loss"][step], step=step + 1)
                    if "val_accuracy" in metrics:
                        mlflow.log_metric("val_accuracy", metrics["val_accuracy"][step], step=step + 1)
                try:
                    import matplotlib.pyplot as plt

                    epochs = list(range(1, len(metrics.get("loss", [])) + 1))
                    if epochs:
                        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
                        axes[0].plot(epochs, metrics.get("accuracy", []), label="train_acc", marker="o")
                        axes[0].plot(epochs, metrics.get("val_accuracy", []), label="val_acc", marker="o")
                        axes[0].set_title("Accuracy")
                        axes[0].set_xlabel("Epoch")
                        axes[0].set_ylabel("Accuracy")
                        axes[0].legend()

                        axes[1].plot(epochs, metrics.get("loss", []), label="train_loss", marker="o")
                        axes[1].plot(epochs, metrics.get("val_loss", []), label="val_loss", marker="o")
                        axes[1].set_title("Loss")
                        axes[1].set_xlabel("Epoch")
                        axes[1].set_ylabel("Loss")
                        axes[1].legend()

                        fig.tight_layout()
                        os.makedirs(os.path.dirname(train_curve_path) or ".", exist_ok=True)
                        fig.savefig(train_curve_path)
                        plt.close(fig)
                except Exception as exc:
                    print(f"Training curve generation failed: {exc}")

            artifact_store_available = _artifact_store_available()
            mlflow.set_tag("artifact_store_available", str(artifact_store_available).lower())
            if not artifact_store_available:
                mlflow.set_tag("artifact_store_status", "skipped_no_endpoint")
                print("Artifact store not available; skipping MLflow artifact upload.")
            else:
                if metrics_path and os.path.exists(metrics_path):
                    _safe_log_artifact(metrics_path, artifact_path="metrics")
                if train_curve_path and os.path.exists(train_curve_path):
                    _safe_log_artifact(train_curve_path, artifact_path="metrics")
                if model_path and os.path.exists(model_path):
                    _safe_log_artifact(model_path, artifact_path="model")

                confusion_saved = eval_result.get("confusion_path")
                sample_grid_saved = eval_result.get("sample_grid_path")
                if confusion_saved and os.path.exists(confusion_saved):
                    _safe_log_artifact(confusion_saved, artifact_path="eval")
                else:
                    if confusion_path and os.path.exists(confusion_path):
                        _safe_log_artifact(confusion_path, artifact_path="eval")
                    elif confusion_csv_path and os.path.exists(confusion_csv_path):
                        _safe_log_artifact(confusion_csv_path, artifact_path="eval")
                if sample_grid_saved and os.path.exists(sample_grid_saved):
                    _safe_log_artifact(sample_grid_saved, artifact_path="eval")

    task_log_to_mlflow = PythonOperator(
        task_id="log_to_mlflow",
        python_callable=_log_to_mlflow,
        op_kwargs={
            "train_result_json": "{{ ti.xcom_pull(task_ids='train_mnist_tf_script') }}",
            "eval_result_json": "{{ ti.xcom_pull(task_ids='evaluate_mnist_tf_script') }}",
            "metrics_path": metrics_path,
            "model_path": model_path,
            "train_curve_path": train_curve_path,
            "confusion_path": confusion_path,
            "confusion_csv_path": confusion_csv_path,
            "experiment_name": MLFLOW_EXPERIMENT_NAME,
            "run_name": "mnist_cnn_train_with_tensorflow",
            "tracking_uri": MLFLOW_TRACKING_URI,
        },
    )

    # ============================================================================
    # DAG Dependencies
    # ============================================================================
    task_train >> task_evaluate >> task_log_to_mlflow
