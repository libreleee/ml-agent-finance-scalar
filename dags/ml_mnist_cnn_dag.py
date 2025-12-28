"""
MNIST CNN Training DAG (CPU) - TensorFlow/Keras via DockerOperator
=================================================================

목표:
- TensorFlow/Keras로 MNIST를 간단히 학습(CPU)하고 결과를 MLflow에 기록합니다.
- 학습은 별도 Docker 이미지(`tensorflow/tensorflow`)에서 수행해 Airflow 컨테이너 의존성을 가볍게 유지합니다.

전제:
- Airflow worker가 `/var/run/docker.sock`에 접근 가능해야 합니다(DockerOperator 사용).
- MLflow는 `MLFLOW_TRACKING_URI`(기본: http://mlflow:5000)로 접근 가능해야 합니다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

try:
    from airflow.providers.docker.operators.docker import DockerOperator
except ModuleNotFoundError:
    from airflow.operators.docker_operator import DockerOperator  # type: ignore

try:
    from airflow.providers.standard.operators.python import PythonOperator
except ModuleNotFoundError:
    from airflow.operators.python import PythonOperator


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=30),
}


def _log_mnist_metrics_to_mlflow(**context):
    import json
    import os

    import mlflow

    ti = context["ti"]
    raw_output = ti.xcom_pull(task_ids="train_mnist_tf")
    if raw_output is None:
        raise ValueError("No XCom output from DockerOperator task 'train_mnist_tf'")

    if isinstance(raw_output, bytes):
        raw_output = raw_output.decode("utf-8", errors="replace")

    last_json_line = None
    for line in reversed(str(raw_output).splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            last_json_line = line
            break
    if last_json_line is None:
        raise ValueError("Could not find JSON result line in DockerOperator logs")

    result = json.loads(last_json_line)

    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("mnist-cnn")

    with mlflow.start_run(run_name="mnist_cnn_cpu_smoke"):
        mlflow.log_param("framework", "tensorflow")
        mlflow.log_param("image", "tensorflow/tensorflow:2.15.0")
        for key in ("epochs", "train_samples", "test_samples"):
            if key in result:
                mlflow.log_param(key, result[key])
        for key in ("test_accuracy", "test_loss", "duration_sec"):
            if key in result:
                mlflow.log_metric(key, result[key])

    return result


with DAG(
    dag_id="mnist_cnn_training",
    default_args=default_args,
    description="MNIST CNN training (TF/Keras in Docker) + MLflow logging",
    schedule_interval=None,  # manual trigger
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mnist", "cnn", "tensorflow", "mlflow", "docker"],
) as dag:
    # ============================================================================
    # Task 1: Train MNIST CNN (TensorFlow/Keras, Docker)
    # ============================================================================
    train_mnist_tf = DockerOperator(
        task_id="train_mnist_tf",
        image="tensorflow/tensorflow:2.15.0",
        api_version="auto",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        auto_remove=True,
        mount_tmp_dir=False,
        do_xcom_push=True,
        command=[
            "bash",
            "-lc",
            """
python - <<'PY'
import json
import time

import numpy as np
import tensorflow as tf
from tensorflow.keras.datasets import mnist

np.random.seed(42)
tf.random.set_seed(42)

start = time.time()
(x_train, y_train), (x_test, y_test) = mnist.load_data()

# 빠른 CPU 스모크 테스트(짧게) - 샘플 수를 줄여서 수 분 내로 끝나도록 구성
x_train = x_train[:5000].astype("float32") / 255.0
y_train = y_train[:5000]
x_test = x_test[:1000].astype("float32") / 255.0
y_test = y_test[:1000]

x_train = np.expand_dims(x_train, -1)
x_test = np.expand_dims(x_test, -1)

model = tf.keras.Sequential([
    tf.keras.layers.Conv2D(16, (3, 3), activation="relu", input_shape=(28, 28, 1)),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Conv2D(32, (3, 3), activation="relu"),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(64, activation="relu"),
    tf.keras.layers.Dense(10, activation="softmax"),
])
model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

model.fit(x_train, y_train, epochs=1, batch_size=64, validation_split=0.1, verbose=2)
test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)

result = {
    "epochs": 1,
    "train_samples": int(x_train.shape[0]),
    "test_samples": int(x_test.shape[0]),
    "test_accuracy": float(test_accuracy),
    "test_loss": float(test_loss),
    "duration_sec": float(time.time() - start),
}
print(json.dumps(result))
PY
""",
        ],
    )

    # ============================================================================
    # Task 2: Log Metrics to MLflow
    # ============================================================================
    log_to_mlflow = PythonOperator(
        task_id="log_to_mlflow",
        python_callable=_log_mnist_metrics_to_mlflow,
    )

    # ============================================================================
    # DAG Dependencies
    # ============================================================================
    train_mnist_tf >> log_to_mlflow
