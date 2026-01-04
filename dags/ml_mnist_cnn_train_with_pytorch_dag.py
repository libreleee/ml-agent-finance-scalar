"""
MNIST CNN Training DAG - train_with_pytorch (in Airflow worker)
==============================================================

이 DAG는 PyTorch/torchvision을 Airflow worker 환경에 직접 설치(pip/커스텀 이미지)한 뒤,
학습 스크립트(`dags/scripts/train_mnist_cnn_pytorch.py`)를 실행하여 MNIST를 CPU로 짧게 학습하고,
결과를 MLflow에 기록하는 예제입니다.

주의:
- Airflow 컨테이너에 `torch`, `torchvision`이 설치되어 있어야 합니다.
- 운영 환경에서는 `train_with_docker`(또는 K8s Pod 실행) 방식이 더 안전합니다.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

try:
    from airflow.providers.standard.operators.bash import BashOperator
except ModuleNotFoundError:
    from airflow.operators.bash import BashOperator

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


with DAG(
    dag_id="mnist_cnn_training_train_with_pytorch",
    default_args=default_args,
    description="MNIST CNN training (PyTorch in Airflow worker) + MLflow logging",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mnist", "cnn", "pytorch", "mlflow", "bash_operator"],
) as dag:
    # ============================================================================
    # Task 1: Train MNIST CNN (PyTorch, python script)
    # ============================================================================
    model_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_pytorch/{{ ts_nodash }}/model.pth"
    run_id_path = "/opt/airflow/dags/artifacts/mnist_cnn_training_train_with_pytorch/{{ ts_nodash }}/run_id.txt"
    task_train = BashOperator(
        task_id="train_mnist_pytorch_script",
        bash_command=(
            "python /opt/airflow/dags/scripts/train_mnist_cnn_pytorch.py "
            f"--model-path '{model_path}' --run-id-path '{run_id_path}'"
        ),
        env={
            "MLFLOW_EXPERIMENT_NAME": MLFLOW_EXPERIMENT_NAME,
            "MLFLOW_RUN_NAME": "mnist_cnn_train",
        },
    )

    # ============================================================================
    # Task 2: Evaluate MNIST CNN (PyTorch, python script)
    # ============================================================================
    task_evaluate = BashOperator(
        task_id="evaluate_mnist_pytorch_script",
        bash_command=(
            "python /opt/airflow/dags/scripts/evaluate_mnist_cnn_pytorch.py "
            f"--model-path '{model_path}' --run-id-path '{run_id_path}'"
        ),
        env={
            "MLFLOW_EXPERIMENT_NAME": MLFLOW_EXPERIMENT_NAME,
            "MLFLOW_RUN_NAME": "mnist_cnn_eval",
        },
    )

    # ============================================================================
    # DAG Dependencies
    # ============================================================================
    task_train >> task_evaluate
