# 데이터 드리프트 + CT(Continuous Training) 운영 프로세스 (우리 시스템 버전)

## 0) 철학
- 자동화는 하되, 금융은 “자동 승격”이 위험할 수 있음
- 따라서:
  - CT는 자동으로 Staging까지
  - Production 승격은 원칙적으로 수동 승인(또는 2중 조건)

---

## 1) 입력(Drift) vs 성능(Performance)
옵션 트레이딩에서는 라벨(수익/PNL)이 지연되기 쉽습니다.
따라서 모니터링을 2층으로 둡니다.

### A) 입력 드리프트(즉시)
- 핵심 피처 분포 변화(PSI/KS/Wasserstein)
- 예측/신호 분포 변화(평균/분산/분위수/엔트로피)
- 체결 품질(슬리피지, fill ratio) 변화

### B) 성능 드리프트(지연)
- T+N 수익률 기반 hit rate
- realized PnL, drawdown, regime별 성능

---

## 2) Baseline(기준선) 관리
### Baseline 생성 시점
- 모델을 Production으로 승격하는 순간

### Baseline 저장 위치(권장 2중)
1) MLflow artifact로 저장 (진실의 원장)
2) (선택) ClickHouse baseline_profiles에 요약 통계 저장(대시보드 편의)

Baseline 내용 예시
- 각 피처별 quantile(0.01/0.05/0.5/0.95/0.99)
- mean/std
- 상관행렬 요약(핵심 피처만)

---

## 3) Drift Job (15분~1시간)
### 입력
- current window: ClickHouse에서 최근 60분 피처 스냅샷 조회
- baseline: MLflow artifact(또는 ClickHouse baseline_profiles)

### 출력
- `ops.drift_reports`에 저장
- warning/critical 판정

### 판정 기준(샘플)
- Warning:
  - 핵심 피처 중 PSI>0.2가 1개라도 등장 OR
  - 신호 분포 평균이 baseline 대비 2σ 이상 이동
- Critical:
  - 핵심 피처 중 PSI>0.3 피처 비율이 20% 이상 AND
  - 보호 조건(슬리피지 급증/연속손실/리스크 이벤트 급증) 중 하나 충족

---

## 4) 보호조치(런타임)
Critical이면 런타임에서 즉시 수행
- 신규 진입 제한(block_new)
- 포지션 축소(reduce)
- 특정 전략 비활성화(disable strategy)
- (선택) shadow 모델로 트래픽 일부 전환

---

## 5) CT 트리거
### 트리거 종류
- 스케줄: 주 1회
- 이벤트: drift_critical
- 성능 붕괴: 지연 레이블 성능 하락

### CT 단계
1) 최신 데이터 스냅샷 선택(Iceberg snapshot)
2) Gold 재생성(필요 시)
3) 학습/튜닝(Ray)
4) 워크포워드 검증
5) MLflow run 기록
6) 후보 모델 Staging 등록
7) 리플레이 검증 통과 시 Production 승격(수동 승인 권장)

---

## 6) 추천 오픈소스
- 데이터 품질(Data Contract): Great Expectations / Deequ
- 드리프트 리포트: Evidently
- 성능 영향 추정(라벨 지연): NannyML(선택)
- 모델 관리: MLflow Registry
