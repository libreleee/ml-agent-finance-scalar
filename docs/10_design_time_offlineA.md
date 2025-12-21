# Design-Time (Offline A) — Spark + Iceberg + Ray + MLflow

## 목표
- 수년치 옵션 틱데이터(콜/풋)로 **피처/라벨/모델/전략을 검증**하고 승격시키는 “공장”
- 핵심: **재현성**, **시점정합(Point-in-time)**, **대규모 실험 병렬화**

## 권장 스택
- Spark: 대규모 ETL/집계 (Structured Streaming은 선택)
- Iceberg: 레이크하우스 테이블, 스냅샷 기반 타임트래블
- Ray: walk-forward/튜닝/백테스트 병렬화 + (선택) 분산 학습
- MLflow: 실험 추적 + 모델 레지스트리(승격/롤백) + 아티팩트 저장(MinIO)

## 데이터 계층
- Bronze: 원본에 가까운 Raw (XML 파싱 결과 “정규화 전” 보관)
- Silver: 스키마 정규화(타입 고정, 타임존, 결측/이상치 처리)
- Gold: 학습/백테스트용 bars/features/labels

## 오프라인 실행 순서
1) XML → Bronze 적재 (Spark)
2) Bronze → Silver 정규화 + 품질검사
3) Silver → Gold (bars/features/labels)
4) Ray로 walk-forward + 튜닝 + 백테스트
5) MLflow run 기록, 후보 모델 Registry(Staging)
6) 오프라인 리플레이 검증 통과 시 Production 승격

## 재현성 필수 기록(5종)
- 데이터 스냅샷: Iceberg snapshot id(또는 dt range)
- 피처 스펙 버전: featurespec hash
- 학습 코드 버전: git commit
- 모델 버전: MLflow run_id + model version/alias
- 실험 환경: python deps, spark/iceberg 버전
