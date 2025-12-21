# MLflow Registry — 승격/롤백 운영 규칙

## 승격 절차(권장)
1) 학습 파이프라인이 run 기록 + 후보 모델 등록(Registry: Staging)
2) 최근 N일 리플레이(수수료/슬리피지 포함) 검증 통과
3) 리스크/비용 체크 통과
4) Production 승격(alias=Production 업데이트)

## 필수 태깅(강력 권장)
- data_snapshot_id: Iceberg snapshot id 또는 dt 범위
- featurespec_hash: 피처 정의 해시(SHA256)
- code_git_sha: 학습 코드 커밋
- label_version: 라벨 산출 규칙 버전
- trading_cost_model: 비용 모델 버전

## 롤백 트리거 예시
- Drift Critical + 보호 조건(연속손실/슬리피지 급증)
- 주문 실패/피처 결측 급증
- 지연 레이블 성능 급락
