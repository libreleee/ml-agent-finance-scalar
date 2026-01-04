"""
MNIST CNN Training DAG (CPU) - TensorFlow/Keras via DockerOperator
=================================================================

목표:
- TensorFlow/Keras로 MNIST를 간단히 학습(CPU)하고 결과를 MLflow에 기록합니다.
- 학습(train)과 평가(evaluate)를 태스크로 **완전 분리**합니다.
- MLflow 로깅은 학습/평가 스크립트에서 직접 수행합니다.
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
    from docker.types import Mount
except Exception:  # pragma: no cover
    Mount = None  # type: ignore

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
    model_path = "/opt/airflow/dags/artifacts/mnist_cnn_training/{{ ts_nodash }}/model.keras"
    run_id_path = "/opt/airflow/dags/artifacts/mnist_cnn_training/{{ ts_nodash }}/run_id.txt"
    install_deps = "python -m pip install --no-cache-dir mlflow==2.9.2 matplotlib==3.8.2"
    train_mnist_tf = DockerOperator(
        task_id="train_mnist_tf",
        image="tensorflow/tensorflow:2.15.0",
        api_version="auto",
        docker_url="unix://var/run/docker.sock",
        network_mode="lakehouse-net",
        auto_remove=True,
        mount_tmp_dir=False,
        do_xcom_push=False,
        mounts=(
            [Mount(source="airflow-dags", target="/opt/airflow/dags", type="volume")] if Mount else None
        ),
        working_dir="/opt/airflow/dags",
        environment={
            "MLFLOW_TRACKING_URI": "http://mlflow:5000",
            "MLFLOW_EXPERIMENT_NAME": "mnist-cnn",
            "MLFLOW_RUN_NAME": "mnist_cnn_train",
        },
        command=[
            "bash",
            "-lc",
            f"{install_deps} && python scripts/train_mnist_cnn_tf.py "
            f"--model-path '{model_path}' --run-id-path '{run_id_path}'",
        ],
    )

    # ============================================================================
    # Task 2: Evaluate MNIST CNN (TensorFlow/Keras, Docker)
    # ============================================================================
    evaluate_mnist_tf = DockerOperator(
        task_id="evaluate_mnist_tf",
        image="tensorflow/tensorflow:2.15.0",
        api_version="auto",
        docker_url="unix://var/run/docker.sock",
        network_mode="lakehouse-net",
        auto_remove=True,
        mount_tmp_dir=False,
        do_xcom_push=False,
        mounts=(
            [Mount(source="airflow-dags", target="/opt/airflow/dags", type="volume")] if Mount else None
        ),
        working_dir="/opt/airflow/dags",
        environment={
            "MLFLOW_TRACKING_URI": "http://mlflow:5000",
            "MLFLOW_EXPERIMENT_NAME": "mnist-cnn",
            "MLFLOW_RUN_NAME": "mnist_cnn_eval",
        },
        command=[
            "bash",
            "-lc",
            f"{install_deps} && python scripts/evaluate_mnist_cnn_tf.py "
            f"--model-path '{model_path}' --run-id-path '{run_id_path}'",
        ],
    )

    # ============================================================================
    # DAG Dependencies
    # ============================================================================
    train_mnist_tf >> evaluate_mnist_tf
