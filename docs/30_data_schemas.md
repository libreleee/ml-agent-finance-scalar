# 데이터 레이크하우스 스키마 (Bronze/Silver/Gold)

본 스키마는 샘플 XML 필드를 기반으로 “옵션 틱 → 분봉 → 피처/라벨”을 위한 최소 구조입니다.

---

## 1) Bronze

### 1.1 bronze_ticks
원천 XML을 타입 캐스팅하여 “그대로” 담는 레벨.

필드:
- src_file STRING
- side STRING (CALL|PUT)
- ymcode STRING
- code STRING
- strike INT
- idate INT
- itime INT
- tdate TIMESTAMP
- tcnt BIGINT
- c DOUBLE
- o DOUBLE
- h DOUBLE
- l DOUBLE
- oi DOUBLE
- ccnt BIGINT
- ingest_ts TIMESTAMP

파티션:
- days(tdate), side

### 1.2 bronze_codes
- src_file STRING
- side STRING
- ymcode STRING
- code STRING
- lastday INT
- ingest_ts TIMESTAMP

파티션:
- side, ymcode

---

## 2) Silver

### 2.1 silver_ticks
정규화된 이벤트(틱).

- ymcode STRING
- side STRING
- code STRING
- strike INT
- ts TIMESTAMP
- tcnt BIGINT
- price DOUBLE
- open DOUBLE
- high DOUBLE
- low DOUBLE
- oi DOUBLE
- ccnt BIGINT
- trade_date DATE
- minute_ts TIMESTAMP
- ingest_ts TIMESTAMP

파티션:
- trade_date, side

### 2.2 dim_contract
코드 파일(옵션 계약 정보)을 차원으로 정리.

- ymcode STRING
- side STRING
- code STRING
- strike INT
- lastday INT
- effective_from DATE
- effective_to DATE

파티션:
- ymcode, side

---

## 3) Gold

### 3.1 gold_bars_1m
- ymcode, side, code, strike
- bar_ts (1m start)
- o, h, l, c
- v (proxy)
- tick_count
- oi_last
- trade_date

파티션:
- trade_date, side

### 3.2 gold_features_1m
- 엔티티 + asof_ts
- f_ret_1, f_ret_5, f_vol_20, f_range_5, f_oi_chg_5, f_spread_proxy, f_iv_proxy
- trade_date

파티션:
- trade_date, side

### 3.3 gold_labels_1m
- 엔티티 + asof_ts
- y_fwd_ret_5, y_fwd_ret_15
- trade_date

파티션:
- trade_date, side

