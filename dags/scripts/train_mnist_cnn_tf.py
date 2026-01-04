"""
Train MNIST CNN with TensorFlow/Keras (script)
=============================================

이 스크립트는 "단독 실행"과 "Airflow에서 호출" 모두를 위해 작성되었습니다.

- 실행 후 마지막 줄에 JSON 결과를 출력합니다(상위 DAG가 파싱하여 MLflow 로깅 등에 사용).
- 빠른 예제/스모크 테스트를 위해 기본값은 작은 샘플/1 epoch 입니다.
- 이 스크립트는 **학습(train)만** 수행하고, 평가는 별도 스크립트에서 수행합니다.

인자/환경변수(선택, 인자가 우선):
- MNIST_TRAIN_SAMPLES (default: 5000)
- MNIST_EPOCHS        (default: 1)
- MNIST_BATCH_SIZE    (default: 64)
- MNIST_EARLY_STOPPING (default: true)
- MNIST_ES_PATIENCE     (default: 2)
- MNIST_ES_MIN_DELTA    (default: 0.0005)
- MNIST_MODEL_PATH    (default: /tmp/mnist_cnn_model.keras)
- MNIST_RUN_ID_PATH   (default: empty)
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


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    value = value.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def main() -> None:
    import numpy as np
    import tensorflow as tf
    from tensorflow.keras.datasets import mnist

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-path",
        default=os.getenv("MNIST_MODEL_PATH", "/tmp/mnist_cnn_model.keras"),
        help="Where to save the trained model (e.g., /opt/airflow/dags/artifacts/.../model.keras)",
    )
    parser.add_argument("--train-samples", type=int, default=_get_int("MNIST_TRAIN_SAMPLES", 5000))
    parser.add_argument("--epochs", type=int, default=_get_int("MNIST_EPOCHS", 1))
    parser.add_argument("--batch-size", type=int, default=_get_int("MNIST_BATCH_SIZE", 64))
    parser.add_argument("--early-stopping", default=os.getenv("MNIST_EARLY_STOPPING", "true"))
    parser.add_argument("--early-stopping-patience", type=int, default=_get_int("MNIST_ES_PATIENCE", 2))
    parser.add_argument("--early-stopping-min-delta", type=float, default=_get_float("MNIST_ES_MIN_DELTA", 0.0005))
    parser.add_argument("--run-id-path", default=os.getenv("MNIST_RUN_ID_PATH", ""))
    parser.add_argument("--metrics-path", default=os.getenv("MNIST_METRICS_PATH", ""))
    parser.add_argument("--mlflow-experiment", default=os.getenv("MLFLOW_EXPERIMENT_NAME", "mnist-cnn"))
    parser.add_argument("--mlflow-run-name", default=os.getenv("MLFLOW_RUN_NAME", "mnist_cnn_train"))
    args = parser.parse_args()

    model_path = args.model_path
    train_samples = args.train_samples
    epochs = args.epochs
    batch_size = args.batch_size
    early_stopping_enabled = str(args.early_stopping).strip().lower() not in {"0", "false", "no", "off"}
    early_stopping_patience = args.early_stopping_patience
    early_stopping_min_delta = args.early_stopping_min_delta
    run_id_path = args.run_id_path.strip()
    metrics_path = args.metrics_path.strip()
    mlflow_experiment = args.mlflow_experiment
    mlflow_run_name = args.mlflow_run_name

    np.random.seed(42)
    tf.random.set_seed(42)

    start = time.time()
    (x_train, y_train), _ = mnist.load_data()

    x_train = x_train[:train_samples].astype("float32") / 255.0
    y_train = y_train[:train_samples]
    x_train = np.expand_dims(x_train, -1)

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

    callbacks = []
    early_stopping_cb = None
    if early_stopping_enabled:
        early_stopping_cb = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=early_stopping_patience,
            min_delta=early_stopping_min_delta,
            restore_best_weights=True,
        )
        callbacks.append(early_stopping_cb)

    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    run_id = None
    mlflow_enabled = bool(mlflow_tracking_uri)
    mlflow = None
    if mlflow_enabled:
        try:
            import mlflow  # type: ignore[no-redef]
        except ModuleNotFoundError:
            mlflow_enabled = False

    history = model.fit(
        x_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=0.1,
        callbacks=callbacks,
        verbose=2,
    )

    os.makedirs(os.path.dirname(model_path) or ".", exist_ok=True)
    model.save(model_path)

    metrics = history.history
    if metrics_path:
        os.makedirs(os.path.dirname(metrics_path) or ".", exist_ok=True)
        with open(metrics_path, "w", encoding="utf-8") as metrics_file:
            json.dump(metrics, metrics_file)

    if mlflow_enabled and mlflow_tracking_uri:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(mlflow_experiment)
        with mlflow.start_run(run_name=mlflow_run_name) as run:
            run_id = run.info.run_id
            mlflow.log_param("framework", "tensorflow")
            mlflow.log_param("stage", "train")
            mlflow.log_param("epochs", epochs)
            mlflow.log_param("train_samples", int(x_train.shape[0]))
            mlflow.log_param("batch_size", batch_size)
            mlflow.log_param("model_path", model_path)
            mlflow.log_param("early_stopping", early_stopping_enabled)
            mlflow.log_param("early_stopping_patience", early_stopping_patience)
            mlflow.log_param("early_stopping_min_delta", early_stopping_min_delta)

            for step in range(len(metrics.get("loss", []))):
                mlflow.log_metric("train_loss", metrics["loss"][step], step=step + 1)
                if "accuracy" in metrics:
                    mlflow.log_metric("train_accuracy", metrics["accuracy"][step], step=step + 1)
                if "val_loss" in metrics:
                    mlflow.log_metric("val_loss", metrics["val_loss"][step], step=step + 1)
                if "val_accuracy" in metrics:
                    mlflow.log_metric("val_accuracy", metrics["val_accuracy"][step], step=step + 1)

            mlflow.log_metric("train_duration_sec", float(time.time() - start))
            if early_stopping_cb is not None:
                mlflow.log_metric("early_stopping_stopped_epoch", float(early_stopping_cb.stopped_epoch))
                if early_stopping_cb.best is not None:
                    mlflow.log_metric("early_stopping_best", float(early_stopping_cb.best))
            try:
                mlflow.log_artifact(model_path, artifact_path="model")
            except Exception as exc:
                print(f"MLflow artifact logging failed: {exc}")
    if run_id and run_id_path:
        os.makedirs(os.path.dirname(run_id_path) or ".", exist_ok=True)
        with open(run_id_path, "w", encoding="utf-8") as run_file:
            run_file.write(run_id)

    result = {
        "framework": "tensorflow",
        "stage": "train",
        "epochs": epochs,
        "train_samples": int(x_train.shape[0]),
        "batch_size": batch_size,
        "model_path": model_path,
        "metrics_path": metrics_path or None,
        "early_stopping": early_stopping_enabled,
        "early_stopping_patience": early_stopping_patience,
        "early_stopping_min_delta": early_stopping_min_delta,
        "early_stopping_stopped_epoch": early_stopping_cb.stopped_epoch if early_stopping_cb else None,
        "early_stopping_best": float(early_stopping_cb.best) if early_stopping_cb and early_stopping_cb.best is not None else None,
        "run_id": run_id,
        "duration_sec": float(time.time() - start),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
