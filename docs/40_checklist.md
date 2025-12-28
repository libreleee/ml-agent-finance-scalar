# 구축/운영 체크리스트 (Offline A + Runtime)

---

## A. 데이터/ETL 체크리스트

- [ ] 원천 XML 스키마(필드/타입) 고정
- [ ] 타임존 정책 결정(UTC 저장 vs KST 저장)
- [ ] 중복 ingest 방지 정책
  - [ ] src_file 기반 idempotent ingest
  - [ ] checksum/manifest 테이블
- [ ] Bronze/Silver/Gold 파티션 전략 확정
- [ ] 데이터 품질 규칙
  - [ ] 결측/이상치 정책(0 가격, 음수, 급등락)
  - [ ] 시간 역전/중복 tick 처리
- [ ] 비용/슬리피지 모델 데이터 확보

---

## B. 오프라인 학습(Research Factory)

- [ ] 워크포워드 폴드 정의(예: 3개월 학습/1주 검증 롤링)
- [ ] 레짐 분리(변동성, 장세, 만기 근접 등)
- [ ] 실험 메트릭 정의
  - [ ] Sharpe / MDD / CVaR
  - [ ] Turnover / 거래비용 민감도
  - [ ] Worst-case 기간 성과
- [ ] Ray 실험 병렬화 설계
- [ ] MLflow Tracking/Registry 구성
  - [ ] 필수 tag: data_snapshot_id, feature_hash, git_commit, cost_model_version
- [ ] 승격(Promotion) 규칙
  - [ ] Staging 기준
  - [ ] Production 기준
  - [ ] 롤백 기준

---

## C. 런타임(Trading Agent)

- [ ] 모델 로딩 전략 확정(A: 시작시 1회 / B: 주기적 핫리로드)
- [ ] Feature parity(오프라인/런타임 일치) 검증
  - [ ] 리플레이 기반 회귀 테스트(최근 N일)
- [ ] Risk Gate 구현
  - [ ] 총 손실 한도
  - [ ] 포지션/델타/감마 노출 한도(옵션이면 중요)
  - [ ] 연속 손실 제한
  - [ ] 슬리피지 급증 감지
- [ ] 주문/체결 실패 안전
  - [ ] 재시도/타임아웃
  - [ ] 부분체결 처리
  - [ ] 네트워크 장애 시 중단/복구
- [ ] Kill Switch
  - [ ] 수동 스위치
  - [ ] 자동 트리거(리스크 이벤트)
- [ ] 모니터링/알림
  - [ ] PnL, hit rate, 체결률, 슬리피지
  - [ ] 모델 드리프트/피처 분포 변화(선택)

