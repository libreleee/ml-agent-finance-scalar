from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
import pandas as pd

import mlflow
from mlflow.models import infer_signature

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

import lightgbm as lgb
import ray
from ray import tune

from spark_jobs.common_spark import build_spark


FEATURE_COLS = [
    "f_ret_1",
    "f_ret_5",
    "f_vol_20",
    "f_range_5",
    "f_oi_chg_5",
    "f_spread_proxy",
    "f_iv_proxy",
]


def load_training_df(spark: SparkSession, features_table: str, labels_table: str) -> pd.DataFrame:
    feats = spark.table(features_table)
    labs = spark.table(labels_table)

    df = feats.join(labs, on=["ymcode","side","code","strike","asof_ts","trade_date"], how="inner")

    # drop rows with null label
    df = df.where(F.col("y_fwd_ret_5").isNotNull())

    # bring to pandas (샘플/POC용)
    pdf = df.select(*(FEATURE_COLS + ["y_fwd_ret_5"])).toPandas()
    pdf = pdf.dropna()
    return pdf


def train_one(config, train_df: pd.DataFrame):
    X = train_df[FEATURE_COLS]
    y = train_df["y_fwd_ret_5"]

    # simple split (POC)
    n = len(train_df)
    split = int(n * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_val, y_val = X.iloc[split:], y.iloc[split:]

    params = {
        "objective": "regression",
        "metric": "rmse",
        "learning_rate": config["learning_rate"],
        "num_leaves": config["num_leaves"],
        "min_data_in_leaf": config["min_data_in_leaf"],
        "feature_fraction": config["feature_fraction"],
        "bagging_fraction": config["bagging_fraction"],
        "bagging_freq": 1,
        "seed": 42,
    }

    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val)

    model = lgb.train(
        params,
        dtrain,
        num_boost_round=2000,
        valid_sets=[dval],
        callbacks=[lgb.early_stopping(50)],
    )

    pred = model.predict(X_val)
    rmse = float(((pred - y_val) ** 2).mean() ** 0.5)
    tune.report(rmse=rmse)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-table", required=True)
    ap.add_argument("--labels-table", required=True)
    ap.add_argument("--mlflow-uri", required=True)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--ray-address", default=None)
    args = ap.parse_args()

    spark = build_spark("train_lgbm_ray_mlflow")

    train_df = load_training_df(spark, args.features_table, args.labels_table)

    mlflow.set_tracking_uri(args.mlflow_uri)
    mlflow.set_experiment(args.experiment)

    ray.init(address=args.ray_address, ignore_reinit_error=True)

    search_space = {
        "learning_rate": tune.loguniform(1e-3, 2e-1),
        "num_leaves": tune.randint(16, 256),
        "min_data_in_leaf": tune.randint(10, 200),
        "feature_fraction": tune.uniform(0.5, 1.0),
        "bagging_fraction": tune.uniform(0.5, 1.0),
    }

    def objective(config):
        with mlflow.start_run():
            mlflow.log_params(config)
            train_one(config, train_df)

    tuner = tune.Tuner(
        tune.with_parameters(objective),
        tune_config=tune.TuneConfig(metric="rmse", mode="min", num_samples=20),
        param_space=search_space,
    )

    results = tuner.fit()
    best = results.get_best_result(metric="rmse", mode="min")
    best_cfg = best.config
    best_rmse = best.metrics["rmse"]

    # Train final model with best config, log to MLflow
    X = train_df[FEATURE_COLS]
    y = train_df["y_fwd_ret_5"]
    model = lgb.LGBMRegressor(
        learning_rate=best_cfg["learning_rate"],
        num_leaves=best_cfg["num_leaves"],
        min_child_samples=best_cfg["min_data_in_leaf"],
        subsample=best_cfg["bagging_fraction"],
        colsample_bytree=best_cfg["feature_fraction"],
        n_estimators=2000,
        random_state=42,
    )
    model.fit(X, y)

    with mlflow.start_run(run_name="best_model_finalize") as run:
        mlflow.log_params(best_cfg)
        mlflow.log_metric("rmse_best", best_rmse)

        signature = infer_signature(X, model.predict(X))
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            signature=signature,
            input_example=X.head(5),
            registered_model_name="options_offlineA_lgbm",
        )

    print("OK: logged and registered model to MLflow Registry (check MLflow UI)")
    ray.shutdown()
    spark.stop()


if __name__ == "__main__":
    main()
