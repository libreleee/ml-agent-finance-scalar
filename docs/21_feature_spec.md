# Feature Spec (옵션 분단위 전략)

이 문서는 “오프라인/런타임 공통 피처 정의서”입니다.

---

## 1) 엔티티 키

- `ymcode` (월물)
- `side` (CALL | PUT)
- `code` (종목코드)
- `strike` (행사가)
- 시간 기준: `asof_ts` (분봉 종료 시각 또는 의사결정 시각)

---

## 2) 기본 바(1m)

오프라인 Gold 테이블 기준(`gold_bars_1m`)

- O/H/L/C
- tick_count
- (옵션) 거래량 v: 샘플에 volume이 없으므로 `ccnt` 또는 `tick_count`로 proxy

---

## 3) 기본 피처(예시)

- 수익률:
  - `f_ret_1`: 1분 수익률 (c_t / c_{t-1} - 1)
  - `f_ret_5`: 5분 수익률
- 변동성:
  - `f_vol_20`: 20분 롤링 std(수익률)
- 레인지/모멘텀:
  - `f_range_5`: 5분 롤링 (h - l) / c
- OI 변화:
  - `f_oi_chg_5`: 5분 OI 변화량(oi_last - oi_last_lag5)
- 스프레드 proxy:
  - 호가가 없는 경우: (h - l) / c 또는 minute range 기반 proxy
- IV proxy(임시):
  - 진짜 IV/Greeks는 기초자산/금리/배당/만기 등이 필요합니다.
  - 초기에는 “IV proxy”로
    - realized vol, range, 또는 옵션 가격 변화율 기반 지표를 사용하고,
  - 추후 확장 시
    - Underlying 가격(선물/현물) + 만기 + 금리 + 배당 + 옵션가격으로
      BS/바이너리/트리 모델 등을 사용하여 IV/Greeks를 계산합니다.

---

## 4) 도메인 특화(확장) 피처 설계 포인트

### Greeks(Delta/Gamma/Vega/Theta)
필수 입력:
- Underlying price (F 또는 S)
- Time-to-maturity (T)
- Risk-free rate (r)
- Dividend yield (q) (필요시)
- Implied volatility (sigma)

구현 전략:
- 오프라인: Spark UDF 또는 Python batch로 IV/Greeks를 산출하여 Gold에 저장
- 런타임: 분 단위라면 “최근 IV/Greeks를 캐시”하거나,
  - 신호 생성 시점에만 계산(캐시 히트율 높이기)

### IV Surface(행사가 x 만기)
- 테이블: (ymcode, ts, strike) 단위로 IV를 저장
- 보간/스무딩: SVI 등은 오프라인에서 학습/보간 후 “표 형태”로 저장
- 런타임: 가장 가까운 strike를 조회하거나, 간단 보간만 수행

### Orderbook depth
- 호가 데이터가 존재하면
  - top-1 spread, imbalance, depth sums 등을 1s 또는 1m 집계
- 런타임은 HFT가 아니므로
  - 1m 집계로도 충분한 경우가 많음

---

## 5) 라벨(예시)

- `y_fwd_ret_5`: 5분 후 수익률
- `y_fwd_ret_15`: 15분 후 수익률

라벨은 전략에 맞게 반드시 재정의하세요.
(예: “진입 후 20분 내 최대 유리 방향 수익” 등)

