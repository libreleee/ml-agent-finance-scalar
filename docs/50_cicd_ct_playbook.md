# CI / CD / CT 운영 플레이북 (우리 시스템)

## CI: 코드/데이터 계약 검증
### 필수
- Lint/Format: ruff/black (선택)
- Unit tests:
  - 피처 계산(오프라인 vs 런타임 일치)
  - 라벨 계산(lookahead 방지)
- Data Contract:
  - Silver/Gold 스키마(필수 컬럼/타입)
  - 품질(결측/범위/중복률/시간 역행)

### 추천(추가)
- Great Expectations로 품질 체크를 자동화
- Spark 잡 결과에 대한 “스모크 검증” (row count, partition 존재 여부)

---

## CD: 런타임 배포
### 원칙
- 런타임은 모델을 포함하지 않는다
- 시작 시 MLflow Registry의 Production alias에서 모델 로드

### 롤백
- 코드 롤백
- MLflow Production alias를 이전 모델로 되돌리기(즉시 효과)

---

## CT: Continuous Training
### 트리거
- schedule: 주 1회(기본)
- drift-critical: repository_dispatch 이벤트로 트리거
- 성능 붕괴: 지연 성능 지표 기반(1일 1회 체크 추천)

### 승격 정책
- Staging까지 자동
- Production 승격은 수동 승인(또는 2중 조건) 권장
