# ml-agent-finance-scalar

옵션(콜/풋) 틱데이터 기반 **Design-Time(오프라인 연구/학습)** ↔ **Runtime(실전 운용)** 분리 아키텍처 & 구현 스켈레톤입니다.

본 레포는 “HFT(마이크로초)”가 아니라, 아래 전제를 둡니다.
- 기본 전략: 분 단위(1m/5m) + 추세/레짐 전략
- 실시간 필요: 런타임 에이전트 동작 시에만 필요
- 도메인 피처: Greeks / IV Surface / orderbook depth 등(확장 설계 포함)

---

## 1) 왜 이 구조가 맞나 (한 줄)
- **Iceberg(Parquet)**: 오프라인 “진실의 원장” (학습/재현성/스냅샷)
- **MLflow**: 모델 “진실의 원장” (승격/롤백/라인리지)
- **ClickHouse**: 런타임 “블랙박스/관측 DB” (드리프트/성능/감사/대시보드)
- **Redis**: 런타임 “짧은 윈도우 캐시” (최근 N분 스냅샷)

---

## 2) 구성요소
### Design-Time(오프라인 공장)
- Spark + Iceberg: Bronze/Silver/Gold (ticks → bars/features/labels)
- Ray: walk-forward / 튜닝 / 병렬 백테스트 / (선택) 분산학습
- MLflow: 실험 추적 + Model Registry(Staging/Production)

### Runtime(실전)
- Runtime Agent: 분봉/피처 계산 → MLflow Production 모델 로드 → 신호 → Risk Gate → 주문
- Observability: runtime_features/predictions/execution/risk/pnl 을 ClickHouse에 적재
- Drift Job: baseline vs current window 비교 → Warning/Critical → CT 트리거

---

## 3) 빠른 시작 (로컬)
### 3.1 Infra 실행 (MLflow + MinIO + Redis + ClickHouse)
```bash
cd infra
docker compose up -d
```

### 3.2 Spark 잡(스켈레톤) 실행
```bash
# Spark/Iceberg 환경 준비 후:
spark-submit spark/jobs/ingest_xml_to_bronze.py \
  --input data/sample_xml/202601_20251201_TICK_CALL.xml \
  --table bronze.raw_ticks

spark-submit spark/jobs/ingest_xml_to_bronze.py \
  --input data/sample_xml/202601_20251219_CODE_CALL.xml \
  --table bronze.raw_codes
```

### 3.3 Offline train(스켈레톤)
```bash
python -m pipelines.train --config pipelines/configs/train_default.yaml
```

### 3.4 Runtime agent(스켈레톤)
```bash
python -m runtime.agent --config runtime/configs/runtime_default.yaml
```

### 3.5 Drift job(스켈레톤 → Evidently로 교체 권장)
```bash
python -m monitoring.drift.run --config monitoring/configs/drift_default.yaml
```

---

## 4) 문서(필독)
- `docs/00_overview.md`
- `docs/11_data_model_bronze_silver_gold.md`
- `docs/12_spark_iceberg_etl_pyspark.md`
- `docs/13_clickhouse_observability_schema.md`
- `docs/40_drift_monitoring_and_ct.md`
- `docs/50_cicd_ct_playbook.md`

---

## 5) 디렉토리
- `data/sample_xml/` : 샘플 XML(콜/풋 틱 + 콜/풋 코드)
- `docs/` : 설계/운영 문서(제목만 있는 문서 없음)
- `spark/` : Spark ETL 스켈레톤(PySpark + Iceberg + spark-xml)
- `pipelines/` : 학습/검증 파이프라인(MLflow Registry 연동)
- `runtime/` : 런타임 에이전트(Production 모델 로드) + ClickHouse 적재
- `monitoring/` : 드리프트 잡(ClickHouse current + MLflow baseline)
- `infra/` : docker compose (MLflow/MinIO/Redis/ClickHouse)
- `.github/workflows/` : CI / CT / Deploy 스켈레톤
- `diagrams/` : Mermaid 다이어그램 (.mmd)

---

## 6) 기존 레포에 덮어쓰기
이 ZIP은 “레포 전체를 덮어써도 되는” 풀 패키지입니다.
- 안전하게 하려면 새 브랜치에서 반영 후 PR 머지 추천
- 덮어쓰더라도, Git history로 되돌릴 수 있습니다.
