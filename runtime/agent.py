from __future__ import annotations

import time
import json
import yaml
from typing import Dict, Any

import pandas as pd


def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_model(cfg: Dict[str, Any]):
    import mlflow
    mlflow.set_tracking_uri(cfg["mlflow"]["tracking_uri"])
    name = cfg["mlflow"]["model_name"]
    alias = cfg["mlflow"]["model_alias"]
    model_uri = f"models:/{name}@{alias}"
    model = mlflow.pyfunc.load_model(model_uri)
    print(f"[RUNTIME] loaded model: {model_uri}")
    return model


def ch_client(cfg: Dict[str, Any]):
    import clickhouse_connect
    ch = cfg["clickhouse"]
    return clickhouse_connect.get_client(
        host=ch["host"],
        port=int(ch["port"]),
        username=ch["username"],
        password=ch["password"],
        database=ch["database"],
        secure=bool(ch.get("secure", False)),
    )


def feature_calc_stub() -> Dict[str, Any]:
    # TODO: 실제 구현에서는 분봉/호가/체결 기반 피처 계산
    return {
        "iv_atm": 0.22,
        "iv_skew": 0.01,
        "bid_ask_spread": 0.1,
        "volume_1m": 1234.0,
        "oi": 1000.0,
        "delta": 0.45,
        "gamma": 0.01,
        "vega": 0.12,
        "theta": -0.03,
    }


def risk_gate_stub(signal: float) -> bool:
    # TODO: 포지션/손실/유동성 체크
    return True


def execute_stub(signal: float):
    # TODO: paper/live 주문 라우팅
    print(f"[EXEC] signal={signal}")


def insert_runtime_snapshot(client, ts_utc: str, ts_local: str, meta: Dict[str, Any], feats: Dict[str, Any], signal: float):
    row_feat = {
        "ts_utc": ts_utc,
        "ts_local": ts_local,
        "ymcode": meta["ymcode"],
        "cp": meta["cp"],
        "code": meta["code"],
        "strike": float(meta["strike"]),
        "model_name": meta["model_name"],
        "model_version": meta["model_version"],
        "model_alias": meta["model_alias"],
        "featurespec_hash": meta["featurespec_hash"],
        "iv_atm": feats.get("iv_atm"),
        "iv_skew": feats.get("iv_skew"),
        "bid_ask_spread": feats.get("bid_ask_spread"),
        "volume_1m": feats.get("volume_1m"),
        "oi": feats.get("oi"),
        "delta": feats.get("delta"),
        "gamma": feats.get("gamma"),
        "vega": feats.get("vega"),
        "theta": feats.get("theta"),
        "extra_json": json.dumps({}, ensure_ascii=False),
    }
    client.insert("runtime_features", [row_feat], column_names=list(row_feat.keys()))

    row_pred = {
        "ts_utc": ts_utc,
        "ts_local": ts_local,
        "ymcode": meta["ymcode"],
        "cp": meta["cp"],
        "code": meta["code"],
        "strike": float(meta["strike"]),
        "model_name": meta["model_name"],
        "model_version": meta["model_version"],
        "model_alias": meta["model_alias"],
        "featurespec_hash": meta["featurespec_hash"],
        "signal": float(signal),
        "confidence": None,
        "pred_json": json.dumps({"signal": signal}, ensure_ascii=False),
    }
    client.insert("runtime_predictions", [row_pred], column_names=list(row_pred.keys()))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    model = load_model(cfg)
    client = ch_client(cfg)

    # Example static meta (실제는 현재 거래 대상 계약을 반영)
    meta = {
        "ymcode": "202601",
        "cp": "CALL",
        "code": "B0161530",
        "strike": 530.0,
        "model_name": cfg["mlflow"]["model_name"],
        "model_version": "unknown",  # TODO: MLflow에서 실제 버전 조회
        "model_alias": cfg["mlflow"]["model_alias"],
        "featurespec_hash": "TODO_SHA256",
    }

    bar_interval = int(cfg["runtime"]["bar_interval_sec"])

    while True:
        feats = feature_calc_stub()
        df = pd.DataFrame([feats])
        pred = model.predict(df)
        signal = float(pred[0]) if hasattr(pred, "__len__") else float(pred)

        if risk_gate_stub(signal):
            execute_stub(signal)

        # timestamps
        ts_utc = pd.Timestamp.utcnow().isoformat()
        ts_local = pd.Timestamp.now(tz=cfg["runtime"]["timezone"]).isoformat()

        # Insert snapshot to ClickHouse (1 row each)
        insert_runtime_snapshot(client, ts_utc, ts_local, meta, feats, signal)

        time.sleep(bar_interval)


if __name__ == "__main__":
    main()
