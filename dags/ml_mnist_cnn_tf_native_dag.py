"""
MNIST CNN Training DAG (CPU) - TensorFlow/Keras native in Airflow Worker
========================================================================

이 DAG는 TensorFlow/Keras를 Airflow worker 환경에 직접 설치(pip/커스텀 이미지)한 뒤,
PythonOperator로 MNIST를 CPU로 짧게 학습하고 MLflow에 기록하는 예제입니다.

주의:
- Airflow 컨테이너에 tensorflow가 설치되어 있어야 합니다.
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


def train_mnist_tf_native():
    import time

    import numpy as np
    import tensorflow as tf
    from tensorflow.keras.datasets import mnist

    np.random.seed(42)
    tf.random.set_seed(42)

    start = time.time()
    (x_train, y_train), (x_test, y_test) = mnist.load_data()

    x_train = x_train[:5000].astype("float32") / 255.0
    y_train = y_train[:5000]
    x_test = x_test[:1000].astype("float32") / 255.0
    y_test = y_test[:1000]

    x_train = np.expand_dims(x_train, -1)
    x_test = np.expand_dims(x_test, -1)

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Conv2D(16, (3, 3), activation="relu", input_shape=(28, 28, 1)),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Conv2D(32, (3, 3), activation="relu"),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dense(10, activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])

    model.fit(x_train, y_train, epochs=1, batch_size=64, validation_split=0.1, verbose=2)
    test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)

    return {
        "framework": "tensorflow",
        "epochs": 1,
        "train_samples": int(x_train.shape[0]),
        "test_samples": int(x_test.shape[0]),
        "test_accuracy": float(test_accuracy),
        "test_loss": float(test_loss),
        "duration_sec": float(time.time() - start),
    }


def log_to_mlflow(**context):
    import os

    import mlflow

    ti = context["ti"]
    result = ti.xcom_pull(task_ids="train_mnist_tf_native")
    if not isinstance(result, dict):
        raise ValueError("Expected dict XCom result from 'train_mnist_tf_native'")

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    with mlflow.start_run(run_name="mnist_cnn_tf_native_cpu_smoke"):
        for key in ("framework", "epochs", "train_samples", "test_samples"):
            if key in result:
                mlflow.log_param(key, result[key])
        for key in ("test_accuracy", "test_loss", "duration_sec"):
            if key in result:
                mlflow.log_metric(key, result[key])

    return result


with DAG(
    dag_id="mnist_cnn_training_tf_native",
    default_args=default_args,
    description="MNIST CNN training (TF/Keras native) + MLflow logging",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mnist", "cnn", "tensorflow", "mlflow", "native"],
) as dag:
    # ============================================================================
    # Task 1: Train MNIST CNN (TensorFlow/Keras, native)
    # ============================================================================
    task_train = PythonOperator(
        task_id="train_mnist_tf_native",
        python_callable=train_mnist_tf_native,
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

