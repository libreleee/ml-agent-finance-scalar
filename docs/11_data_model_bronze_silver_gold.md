# Bronze / Silver / Gold 데이터 모델 (옵션 틱 기준)

이 문서는 “옵션 틱 XML”을 Spark+Iceberg에 적재할 때의 **실제 테이블 스키마**를 제안합니다.  
샘플 XML 구조는 `data/sample_xml/*.xml`을 기준으로 작성했습니다.

---

## 공통 규칙
### 1) 시간
- 원본 XML은 `tdate`에 `+09:00` 포함(ISO8601)
- Iceberg 저장은 **UTC timestamp**로 표준화(컬럼: `ts_utc`)
- 원본 timestamp는 보존(컬럼: `ts_local`)

### 2) 엔티티 키
- `ymcode` (월물, 예: 202601)
- `code` (옵션 종목 코드, 예: B0161530)
- `cp` (CALL/PUT) — 파일명 또는 코드 테이블로 추론
- `strike` (행사가) — tick의 `strike` 또는 code의 `lastday`에서 추정(현 데이터에서는 의미 확인 필요)

### 3) 파티셔닝
- Iceberg 테이블 파티션:
  - ticks: `days(ts_utc)` + `cp` + `ymcode`
  - bars/features/labels: `days(bar_ts_utc)` + `cp` + `ymcode`

---

## Bronze

### bronze.raw_ticks
원본 tick 레코드를 거의 그대로 보존합니다.

| 컬럼 | 타입 | 설명 |
|---|---:|---|
| ingest_ts | timestamp | 적재 시간(UTC) |
| source_file | string | 원본 파일명 |
| cp | string | CALL/PUT |
| ymcode | string | 월물 |
| code | string | 옵션 코드 |
| strike | double | 행사가 |
| idate | int | 원본 날짜(YYYYMMDD) |
| itime | int | 원본 시각(HHMMSS) |
| ts_local | timestamp | 원본 tdate 파싱 timestamp(+09) |
| ts_utc | timestamp | 표준 UTC timestamp |
| tcnt | int | tick count(원본 필드) |
| c | double | 가격(원본 필드) |
| o | double | open(원본 필드) |
| h | double | high(원본 필드) |
| l | double | low(원본 필드) |
| oi | double | open interest(원본 필드) |
| ccnt | int | count(원본 필드) |

권장 Iceberg 옵션
- file format: Parquet
- write.distribution-mode: hash
- sort: (`ymcode`, `cp`, `code`, `ts_utc`)

---

### bronze.raw_codes
콜/풋 코드 목록(샘플 XML 기준)

| 컬럼 | 타입 | 설명 |
|---|---:|---|
| ingest_ts | timestamp | 적재 시간 |
| source_file | string | 파일명 |
| cp | string | CALL/PUT |
| ymcode | string | 월물 |
| code | string | 옵션 코드 |
| lastday | int | 원본 필드(현재 샘플에서는 strike 계열로 보이나 의미 확인 필요) |

---

## Silver

### silver.ticks
Bronze의 타입/정합성/중복을 정리한 버전입니다.

추가 규칙
- `ts_utc` 기준 중복 제거: (ymcode, cp, code, ts_utc)로 중복 제거(최신 ingest_ts 우선)
- `price` 표준 컬럼 추가: `price = c` (필요 시 OHLC 정리)

| 컬럼 | 타입 |
|---|---:|
| ymcode | string |
| cp | string |
| code | string |
| strike | double |
| ts_utc | timestamp |
| price | double |
| o | double |
| h | double |
| l | double |
| oi | double |
| tcnt | int |
| ccnt | int |
| source_file | string |
| ingest_ts | timestamp |

---

### silver.dim_contract
코드/월물/콜풋/행사가 등 계약 차원의 차원 테이블

| 컬럼 | 타입 | 설명 |
|---|---:|---|
| ymcode | string | 월물 |
| cp | string | CALL/PUT |
| code | string | 옵션 코드 |
| strike | double | tick 기반 strike(우선) |
| strike_from_code | double | code 파일(lastday) 기반 추정 |
| first_seen_ts_utc | timestamp | 최초 등장 |
| last_seen_ts_utc | timestamp | 최종 등장 |

---

## Gold

Gold는 “학습/백테스트”에 최적화합니다.

### gold.bars_1m
| 컬럼 | 타입 | 설명 |
|---|---:|---|
| ymcode | string | 월물 |
| cp | string | CALL/PUT |
| code | string | 옵션 코드 |
| strike | double | 행사가 |
| bar_ts_utc | timestamp | 봉 시작 시각(UTC) |
| open | double | |
| high | double | |
| low | double | |
| close | double | |
| volume_ticks | int | tcnt 합 또는 tick 수 |
| oi_last | double | 마지막 oi |
| spread_proxy | double | (확장) bid-ask proxy(현재 샘플엔 호가가 없어서 placeholder) |

---

### gold.features_1m
1m 봉 기반 피처 테이블(학습/서빙 공통)

필수 키
- (ymcode, cp, code, bar_ts_utc)

예시 피처 컬럼(확장 가능)
- returns_1m, returns_5m
- vol_30m, vol_120m
- momentum_15m
- oi_change_5m
- iv_atm, iv_skew (옵션: 별도 IV 테이블을 조인해 채움)
- delta/gamma/vega/theta (옵션: Greeks 계산 테이블 조인)

---

### gold.labels_1m
라벨(예: 미래 N분 수익률, 방향, 손익)

예시
- y_ret_5m = log(close[t+5]/close[t])
- y_dir_5m = sign(y_ret_5m)
- y_ret_30m

---

## 옵션 도메인 확장 테이블(설계만 포함)
샘플 XML에는 호가/기초자산/금리가 없으므로, 아래는 확장 설계입니다.

### gold.iv_surface_snapshot
- ts_utc, ymcode, expiry, strike, cp, iv, iv_bid, iv_ask, underlying_px, rate, dividend_yield

### gold.greeks_snapshot
- ts_utc, contract_id, delta, gamma, vega, theta, rho, iv_used, underlying_px, rate

### gold.orderbook_depth_1m
- bar_ts_utc, contract_id, depth_1, depth_5, imbalance, microprice_proxy 등

---

## 주의: code 파일 lastday 의미
샘플에서 `lastday`가 300, 302 … 형태로 나타나는데 “날짜”라기보다 “행사가 계열”처럼 보입니다.
- 현 단계에서는 `strike_from_code`로 저장하고,
- tick의 `strike`와 교차 검증 후, 의미가 확정되면 컬럼명을 변경하세요.
