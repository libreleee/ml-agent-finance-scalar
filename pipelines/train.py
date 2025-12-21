from __future__ import annotations

import os
import yaml
from typing import Dict, Any

import pandas as pd


def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_cfg(args.config)

    import mlflow
    mlflow.set_tracking_uri(cfg["mlflow"]["tracking_uri"])
    mlflow.set_experiment(cfg["mlflow"]["experiment"])

    # TODO: 실제 구현에서는 Iceberg Gold에서 데이터를 로딩해 pandas/arrow로 가져오세요.
    # 여기서는 스켈레톤 형태로 더미 데이터를 만듭니다.
    X = pd.DataFrame([{"iv_atm": 0.22, "bid_ask_spread": 0.1, "volume_1m": 1200, "delta": 0.45},
                      {"iv_atm": 0.25, "bid_ask_spread": 0.12, "volume_1m": 900, "delta": 0.52}])
    y = pd.Series([0.01, -0.02], name="y_ret_5m")

    model_type = cfg["model"]["type"].lower()

    with mlflow.start_run():
        mlflow.log_param("model_type", model_type)
        for k, v in cfg["model"]["params"].items():
            mlflow.log_param(k, v)

        if model_type == "lightgbm":
            import lightgbm as lgb
            params = cfg["model"]["params"]
            reg = lgb.LGBMRegressor(**params)
            reg.fit(X, y)
            mlflow.lightgbm.log_model(reg, artifact_path="model")
        else:
            # placeholder for DL
            os.makedirs("artifacts", exist_ok=True)
            with open("artifacts/model.txt", "w", encoding="utf-8") as f:
                f.write("placeholder model\n")
            mlflow.log_artifact("artifacts/model.txt", artifact_path="model")

        mlflow.log_metric("valid_sharpe_proxy", 1.23)

        if cfg["promotion"]["register_to_model_registry"]:
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/model"
            name = cfg["promotion"]["model_name"]

            # Register and set alias (requires MLflow 2.9+)
            mv = mlflow.register_model(model_uri, name)
            mlflow.set_registered_model_alias(name, cfg["promotion"]["target_alias"], mv.version)

            # Lineage tags (example placeholders)
            mlflow.set_tag("featurespec_hash", "TODO_SHA256")
            mlflow.set_tag("data_snapshot_id", "TODO_ICEBERG_SNAPSHOT")
            mlflow.set_tag("label_version", "v1")
            mlflow.set_tag("trading_cost_model", "v1")

    print("[TRAIN] done. Check MLflow UI/Registry.")


if __name__ == "__main__":
    main()
