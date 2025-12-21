from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Dict, Any, List

import yaml
import pandas as pd


@dataclass
class DriftResult:
    ts_utc: int
    warning: bool
    critical: bool
    critical_ratio: float
    feature_scores: Dict[str, float]


def load_cfg(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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


def compute_psi_simple(baseline: List[float], current: List[float]) -> float:
    # NOTE: 스켈레톤용 간단 PSI. 실제는 Evidently로 교체 추천.
    if len(baseline) < 2 or len(current) < 2:
        return 0.0
    b_mean = sum(baseline) / len(baseline)
    c_mean = sum(current) / len(current)
    diff = abs(c_mean - b_mean)
    denom = abs(b_mean) + 1e-9
    return float(min(1.0, diff / denom))


def fetch_current_window(client, feature: str, window_minutes: int) -> List[float]:
    q = f"""SELECT {feature}
            FROM ops.runtime_features
            WHERE ts_utc >= now64(3) - INTERVAL {int(window_minutes)} MINUTE
              AND {feature} IS NOT NULL
            LIMIT 50000"""
    rows = client.query(q).result_rows
    return [float(r[0]) for r in rows if r and r[0] is not None]


def load_baseline_from_mlflow(cfg: Dict[str, Any]) -> Dict[str, List[float]]:
    # NOTE: 스켈레톤. 실제로는 MLflow artifact(profile.json)를 가져오세요.
    # 여기서는 예시 baseline을 리턴합니다.
    feats = cfg["features"]["key_features"]
    out: Dict[str, List[float]] = {}
    for f in feats:
        out[f] = [100.0, 101.0, 99.5, 100.2, 100.1]
    return out


def write_result_to_clickhouse(client, cfg: Dict[str, Any], res: DriftResult):
    model_name = cfg["mlflow"]["model_name"]
    model_alias = cfg["mlflow"]["model_alias"]
    row = {
        "ts_utc": int(res.ts_utc),
        "model_name": model_name,
        "model_version": "unknown",
        "model_alias": model_alias,
        "featurespec_hash": "TODO_SHA256",
        "baseline_days": int(cfg["baseline"]["days"]),
        "window_minutes": int(cfg["current"]["window_minutes"]),
        "warning": 1 if res.warning else 0,
        "critical": 1 if res.critical else 0,
        "critical_ratio": float(res.critical_ratio),
        "feature_scores_json": json.dumps(res.feature_scores, ensure_ascii=False),
    }
    client.insert("drift_reports", [row], column_names=list(row.keys()))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    client = ch_client(cfg)

    feats = cfg["features"]["key_features"]
    psi_warning = float(cfg["thresholds"]["psi_warning"])
    psi_critical = float(cfg["thresholds"]["psi_critical"])
    critical_ratio_th = float(cfg["thresholds"]["critical_feature_ratio"])
    window_minutes = int(cfg["current"]["window_minutes"])

    baseline = load_baseline_from_mlflow(cfg)

    scores: Dict[str, float] = {}
    critical_cnt = 0

    for f in feats:
        cur = fetch_current_window(client, f, window_minutes)
        psi = compute_psi_simple(baseline.get(f, []), cur)
        scores[f] = psi
        if psi >= psi_critical:
            critical_cnt += 1

    ratio = critical_cnt / max(1, len(feats))
    warning = any(v >= psi_warning for v in scores.values())
    critical = ratio >= critical_ratio_th

    res = DriftResult(
        ts_utc=int(time.time()),
        warning=warning,
        critical=critical,
        critical_ratio=ratio,
        feature_scores=scores,
    )

    print(f"[DRIFT] warning={res.warning} critical={res.critical} critical_ratio={res.critical_ratio:.3f}")
    print(json.dumps(res.feature_scores, ensure_ascii=False, indent=2))

    if cfg["outputs"].get("write_to_clickhouse", True):
        write_result_to_clickhouse(client, cfg, res)
        print("[DRIFT] wrote to ClickHouse ops.drift_reports")

    # TODO: critical이면 GitHub repository_dispatch(drift_critical) 트리거


if __name__ == "__main__":
    main()
