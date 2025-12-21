# Runtime — 모델 로드 + 피처 + 리스크 + 주문 (분단위 전략)

## 목표
- 런타임 에이전트가 동작할 때만 실시간 필요
- 핵심: **안정성, 롤백, 리스크 게이트, 관측성(로그/지표)**

## 최소 구성
1) Market Data Ingest
2) Bar Builder (1m/5m)
3) Feature Calculator (공유 라이브러리)
4) Redis Cache (최근 윈도우/스냅샷)
5) Inference (MLflow Production 모델 로드)
6) Risk Gate
7) Execution (paper/live)
8) Logs/Metrics (선택: ClickHouse/Druid)

## 모델 로딩
- 기본: 시작 시 Production 모델 1회 로드
- 옵션: 주기적 alias 확인 후 핫리로드(안전 스왑)
- 실패 안전: 로드 실패 시 거래 중단 or 직전 Production으로 자동 복구
