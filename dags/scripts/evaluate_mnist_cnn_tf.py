"""
Evaluate MNIST CNN with TensorFlow/Keras (script)
================================================

이 스크립트는 "단독 실행"과 "Airflow에서 호출" 모두를 위해 작성되었습니다.

- 학습된 모델 파일을 로드하여 MNIST 테스트셋으로 평가(evaluate)합니다.
- 실행 후 마지막 줄에 JSON 결과를 출력합니다(상위 DAG가 파싱하여 MLflow 로깅 등에 사용).

인자/환경변수(선택, 인자가 우선):
- MNIST_MODEL_PATH    (required for Airflow; default: /tmp/mnist_cnn_model.keras)
- MNIST_TEST_SAMPLES  (default: 1000)
- MNIST_RUN_ID_PATH   (default: empty)
- MLFLOW_EXPERIMENT_NAME (default: mnist-cnn)
- MLFLOW_RUN_NAME        (default: mnist_cnn_eval)
- MNIST_SAMPLE_COUNT     (default: 10)
- MNIST_SAMPLE_GRID_PATH (default: empty; model dir에 sample_predictions.png 저장)
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
    import numpy as np
    import tensorflow as tf
    from tensorflow.keras.datasets import mnist

    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default=os.getenv("MNIST_MODEL_PATH", "/tmp/mnist_cnn_model.keras"))
    parser.add_argument("--test-samples", type=int, default=_get_int("MNIST_TEST_SAMPLES", 1000))
    parser.add_argument("--run-id-path", default=os.getenv("MNIST_RUN_ID_PATH", ""))
    parser.add_argument("--confusion-path", default=os.getenv("MNIST_CONFUSION_PATH", ""))
    parser.add_argument("--confusion-csv-path", default=os.getenv("MNIST_CONFUSION_CSV_PATH", ""))
    parser.add_argument("--sample-grid-path", default=os.getenv("MNIST_SAMPLE_GRID_PATH", ""))
    parser.add_argument("--sample-count", type=int, default=_get_int("MNIST_SAMPLE_COUNT", 10))
    parser.add_argument("--mlflow-experiment", default=os.getenv("MLFLOW_EXPERIMENT_NAME", "mnist-cnn"))
    parser.add_argument("--mlflow-run-name", default=os.getenv("MLFLOW_RUN_NAME", "mnist_cnn_eval"))
    args = parser.parse_args()

    model_path = args.model_path
    test_samples = args.test_samples
    run_id_path = args.run_id_path.strip()
    confusion_path = args.confusion_path.strip()
    confusion_csv_path = args.confusion_csv_path.strip()
    sample_grid_path = args.sample_grid_path.strip()
    sample_count = max(1, args.sample_count)
    mlflow_experiment = args.mlflow_experiment
    mlflow_run_name = args.mlflow_run_name

    np.random.seed(42)
    tf.random.set_seed(42)

    start = time.time()
    (_, _), (x_test, y_test) = mnist.load_data()

    x_test = x_test[:test_samples].astype("float32") / 255.0
    y_test = y_test[:test_samples]
    x_test = np.expand_dims(x_test, -1)

    model = tf.keras.models.load_model(model_path)
    test_loss, test_accuracy = model.evaluate(x_test, y_test, verbose=0)

    y_pred = model.predict(x_test, verbose=0)
    y_pred_labels = np.argmax(y_pred, axis=1)
    confusion = np.zeros((10, 10), dtype=int)
    for true_label, pred_label in zip(y_test, y_pred_labels):
        confusion[int(true_label), int(pred_label)] += 1

    base_dir = os.path.dirname(model_path) or "."
    if not confusion_path:
        confusion_path = os.path.join(base_dir, "confusion_matrix.png")
    if not confusion_csv_path:
        confusion_csv_path = os.path.join(base_dir, "confusion_matrix.csv")
    if not sample_grid_path:
        sample_grid_path = os.path.join(base_dir, "sample_predictions.png")

    confusion_saved = None
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 6))
        im = ax.imshow(confusion, cmap="Blues")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title("MNIST Confusion Matrix")
        fig.tight_layout()
        os.makedirs(os.path.dirname(confusion_path) or ".", exist_ok=True)
        fig.savefig(confusion_path)
        plt.close(fig)
        confusion_saved = confusion_path
    except Exception:
        os.makedirs(os.path.dirname(confusion_csv_path) or ".", exist_ok=True)
        with open(confusion_csv_path, "w", encoding="utf-8") as cm_file:
            for row in confusion:
                cm_file.write(",".join(str(value) for value in row))
                cm_file.write("\n")
        confusion_saved = confusion_csv_path

    sample_grid_saved = None
    try:
        import matplotlib.pyplot as plt

        sample_count = min(sample_count, int(x_test.shape[0]))
        indices = np.random.choice(len(x_test), sample_count, replace=False)
        cols = min(5, sample_count)
        rows = int(np.ceil(sample_count / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3))
        axes = np.atleast_1d(axes).ravel()

        for idx, sample_idx in enumerate(indices):
            ax = axes[idx]
            image = x_test[sample_idx].squeeze()
            true_label = int(y_test[sample_idx])
            pred_label = int(y_pred_labels[sample_idx])
            ax.imshow(image, cmap="gray")
            ax.set_title(
                f"True: {true_label}\nPred: {pred_label}",
                color="green" if true_label == pred_label else "red",
            )
            ax.axis("off")
        for ax in axes[sample_count:]:
            ax.axis("off")

        fig.tight_layout()
        os.makedirs(os.path.dirname(sample_grid_path) or ".", exist_ok=True)
        fig.savefig(sample_grid_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        sample_grid_saved = sample_grid_path
    except Exception as exc:
        print(f"Sample grid generation failed: {exc}")

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

        mlflow.log_param("framework", "tensorflow")
        mlflow.log_param("stage", "evaluate")
        mlflow.log_param("model_path", model_path)
        mlflow.log_param("test_samples", int(x_test.shape[0]))
        mlflow.log_metric("test_accuracy", float(test_accuracy))
        mlflow.log_metric("test_loss", float(test_loss))
        mlflow.log_metric("eval_duration_sec", float(time.time() - start))

        if confusion_saved:
            try:
                mlflow.log_artifact(confusion_saved, artifact_path="eval")
            except Exception as exc:
                print(f"MLflow artifact logging failed: {exc}")
        if sample_grid_saved:
            try:
                mlflow.log_artifact(sample_grid_saved, artifact_path="eval")
            except Exception as exc:
                print(f"MLflow artifact logging failed: {exc}")

        mlflow.end_run()

    result = {
        "framework": "tensorflow",
        "stage": "evaluate",
        "model_path": model_path,
        "test_samples": int(x_test.shape[0]),
        "test_accuracy": float(test_accuracy),
        "test_loss": float(test_loss),
        "confusion_path": confusion_saved,
        "sample_grid_path": sample_grid_saved,
        "run_id": run_id,
        "duration_sec": float(time.time() - start),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
