from __future__ import annotations

import os
import time
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional

import redis
import mlflow
import pandas as pd


@dataclass
class RuntimeConfig:
    mlflow_uri: str = "http://localhost:5000"
    model_name: str = "options_offlineA_lgbm"
    model_stage: str = "Production"  # or "Staging"
    redis_host: str = "localhost"
    redis_port: int = 6379


FEATURE_COLS = [
    "f_ret_1",
    "f_ret_5",
    "f_vol_20",
    "f_range_5",
    "f_oi_chg_5",
    "f_spread_proxy",
    "f_iv_proxy",
]


class TradingAgent:
    def __init__(self, cfg: RuntimeConfig):
        self.cfg = cfg
        self.r = redis.Redis(host=cfg.redis_host, port=cfg.redis_port, decode_responses=True)

        mlflow.set_tracking_uri(cfg.mlflow_uri)
        self.model = self._load_model()

    def _load_model(self):
        # Load model from MLflow Registry (stage)
        # Example URI:
        #   models:/options_offlineA_lgbm/Production
        uri = f"models:/{self.cfg.model_name}/{self.cfg.model_stage}"
        model = mlflow.pyfunc.load_model(uri)
        return model

    def _get_features_from_cache(self, key: str) -> Optional[Dict[str, float]]:
        v = self.r.get(key)
        if v is None:
            return None
        return json.loads(v)

    def predict(self, feature_dict: Dict[str, float]) -> float:
        df = pd.DataFrame([feature_dict], columns=FEATURE_COLS)
        pred = float(self.model.predict(df)[0])
        return pred

    def run_once(self, key: str) -> Dict[str, Any]:
        feat = self._get_features_from_cache(key)
        if feat is None:
            return {"ok": False, "reason": "no_features_in_cache", "key": key}

        # Minimal risk gate placeholder
        pred = self.predict(feat)
        decision = "HOLD"
        if pred > 0.001:
            decision = "BUY"
        elif pred < -0.001:
            decision = "SELL"

        return {
            "ok": True,
            "key": key,
            "pred": pred,
            "decision": decision,
        }


def main():
    cfg = RuntimeConfig()
    agent = TradingAgent(cfg)

    # Example key:
    #  options:202601:CALL:B0161530:530:2025-12-01T10:05:00Z
    key = os.environ.get("RUNTIME_FEATURE_KEY", "")
    if not key:
        print("Set env RUNTIME_FEATURE_KEY to a Redis key that contains feature JSON.")
        return

    out = agent.run_once(key)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
