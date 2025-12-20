# Runtime Trading Agent 아키텍처

이 문서는 “오프라인에서 만든 Production 모델을 런타임 에이전트가 로드하여”
분 단위 실시간 트레이딩을 수행하는 구조를 설명합니다.

---

## 1) 오프라인 vs 런타임 차이

### 오프라인(Research/Training)
- 목적: 피처/라벨/모델/전략을 만들고 검증하여 “승격”
- 중요: 재현성(데이터 스냅샷, 코드 버전, 실험 기록)
- 실시간성: 거의 불필요

### 런타임(Runtime)
- 목적: 실시간(분 단위) 시세로 신호 생성 → 리스크 게이트 → 주문
- 중요: 지연(latency), 안정성, 실패 안전, 롤백
- 실시간성: 에이전트 동작 중에만 필요 (상시 스트리밍 플랫폼이 “필수”는 아님)

---

## 2) 런타임 구성요소

- MarketData Ingest (브로커/거래소 데이터 수신)
- Bar Builder (1m/5m)
- Feature Calculator (공유 피처 스펙)
- Redis Cache (최근 N분 윈도우/스냅샷)
- Inference (MLflow Registry Production 모델 로드)
- Risk Gate (손실/노출/연속손실/슬리피지/유동성)
- Execution Engine (주문/취소/재시도/체결 처리)
- Logging/Monitoring (PnL, 슬리피지, 체결률)

---

## 3) 모델 로딩 전략

### A) 에이전트 시작 시 1회 로드(가장 단순/안정)
- 에이전트가 켜질 때 Production 모델을 1회 로드
- 운영 중 모델 변경은 재시작 또는 수동 reload

### B) 주기적 체크(예: 5분마다 Production 버전 변경 확인)
- Registry 버전이 변경되면 안전하게 핫리로드(세이프 스왑)
- 로딩 실패 시 이전 Production 버전으로 자동 복구

본 레포의 기본은 A 또는 B를 권장합니다(HFT가 아니므로).

---

## 4) Feature Parity(오프라인 ↔ 런타임 일치)

런타임 성능은 “모델”보다 “피처 일치”에서 많이 깨집니다.

필수 원칙:

- `docs/21_feature_spec.md`를 단일 진실(Single Source of Truth)로 유지
- 오프라인과 런타임이 가능한 한 동일한 피처 계산 코드를 공유
- 리플레이 회귀 테스트(최근 N일)로 승격 전 검증

---

## 5) 실패 안전(Fail-safe) / Kill Switch

- 모델 로드 실패: 거래 중단 or 이전 Production 자동 복구
- 데이터 지연/결측: 거래 중단 or 보수적 모드
- 리스크 한도 도달: 신규 진입 금지, 포지션 축소/청산

