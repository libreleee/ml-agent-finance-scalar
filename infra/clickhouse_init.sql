
CREATE DATABASE IF NOT EXISTS ops;

-- 1) 런타임 피처 스냅샷
CREATE TABLE IF NOT EXISTS ops.runtime_features
(
    ts_utc           DateTime64(3, 'UTC'),
    ts_local         DateTime64(3, 'Asia/Seoul'),
    ymcode           String,
    cp               LowCardinality(String),
    code             String,
    strike           Float64,

    model_name       LowCardinality(String),
    model_version    String,
    model_alias      LowCardinality(String),
    featurespec_hash String,

    -- 핵심 피처(예시)
    iv_atm           Nullable(Float64),
    iv_skew          Nullable(Float64),
    bid_ask_spread   Nullable(Float64),
    volume_1m        Nullable(Float64),
    oi               Nullable(Float64),
    delta            Nullable(Float64),
    gamma            Nullable(Float64),
    vega             Nullable(Float64),
    theta            Nullable(Float64),

    extra_json       String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts_utc)
ORDER BY (ymcode, cp, code, ts_utc);

-- 2) 예측/신호
CREATE TABLE IF NOT EXISTS ops.runtime_predictions
(
    ts_utc           DateTime64(3, 'UTC'),
    ts_local         DateTime64(3, 'Asia/Seoul'),
    ymcode           String,
    cp               LowCardinality(String),
    code             String,
    strike           Float64,

    model_name       LowCardinality(String),
    model_version    String,
    model_alias      LowCardinality(String),
    featurespec_hash String,

    signal           Float64,
    confidence       Nullable(Float64),
    pred_json        String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts_utc)
ORDER BY (ymcode, cp, code, ts_utc);

-- 3) 주문/체결 이벤트
CREATE TABLE IF NOT EXISTS ops.execution_events
(
    ts_utc        DateTime64(3, 'UTC'),
    ts_local      DateTime64(3, 'Asia/Seoul'),
    event_type    LowCardinality(String),   -- order_new / cancel / fill / reject / error
    order_id      String,
    parent_id     String,
    ymcode        String,
    cp            LowCardinality(String),
    code          String,
    strike        Float64,

    side          LowCardinality(String),   -- buy/sell
    qty           Float64,
    price         Nullable(Float64),
    fill_qty      Nullable(Float64),
    fill_price    Nullable(Float64),

    slippage      Nullable(Float64),
    fee           Nullable(Float64),
    latency_ms    Nullable(UInt32),

    status        LowCardinality(String),
    err_code      String,
    err_msg       String,

    meta_json     String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts_utc)
ORDER BY (ymcode, cp, code, ts_utc, order_id);

-- 4) 리스크 이벤트
CREATE TABLE IF NOT EXISTS ops.risk_events
(
    ts_utc        DateTime64(3, 'UTC'),
    ts_local      DateTime64(3, 'Asia/Seoul'),
    severity      LowCardinality(String),   -- info/warn/critical
    rule_id       LowCardinality(String),   -- max_loss, exposure, etc.
    action        LowCardinality(String),   -- block_new, reduce, close_all
    ymcode        String,
    cp            LowCardinality(String),
    code          String,
    strike        Float64,

    value         Nullable(Float64),
    threshold     Nullable(Float64),
    message       String,
    meta_json     String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts_utc)
ORDER BY (severity, rule_id, ts_utc);

-- 5) PnL (분 단위)
CREATE TABLE IF NOT EXISTS ops.pnl_minute
(
    bar_ts_utc    DateTime64(0, 'UTC'),
    bar_ts_local  DateTime64(0, 'Asia/Seoul'),
    strategy_id   LowCardinality(String),
    pnl_realized  Float64,
    pnl_unreal    Float64,
    exposure      Float64,
    drawdown      Float64,
    trades        UInt32,
    meta_json     String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(bar_ts_utc)
ORDER BY (strategy_id, bar_ts_utc);

-- 6) 드리프트 리포트(배치 잡 결과)
CREATE TABLE IF NOT EXISTS ops.drift_reports
(
    ts_utc            DateTime64(0, 'UTC'),
    model_name        LowCardinality(String),
    model_version     String,
    model_alias       LowCardinality(String),
    featurespec_hash  String,

    baseline_days     UInt32,
    window_minutes    UInt32,

    warning           UInt8,
    critical          UInt8,
    critical_ratio    Float64,

    feature_scores_json String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts_utc)
ORDER BY (model_name, ts_utc);

-- 7) (선택) baseline profile(대시보드 편의용)
CREATE TABLE IF NOT EXISTS ops.baseline_profiles
(
    created_ts_utc     DateTime64(0, 'UTC'),
    model_name         LowCardinality(String),
    model_version      String,
    model_alias        LowCardinality(String),
    featurespec_hash   String,
    baseline_days      UInt32,
    profile_json       String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(created_ts_utc)
ORDER BY (model_name, created_ts_utc);
