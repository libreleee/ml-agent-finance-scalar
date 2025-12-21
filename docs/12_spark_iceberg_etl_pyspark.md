# PySpark + Iceberg ETL (XML → Bronze/Silver/Gold)

본 문서는 Spark로 XML을 적재하는 방법과 ETL 잡 구조를 제공합니다.

---

## 1) Spark 의존성
### spark-xml
- `com.databricks:spark-xml_2.12` 사용

### Iceberg
- 배포 환경에 따라 Iceberg catalog(Nessie/HMS/Glue 등) 설정

---

## 2) 실행 흐름
1) `spark/jobs/ingest_xml_to_bronze.py`
   - XML 파일에서 rowTag(첫 레코드 태그)를 자동 감지
   - spark-xml로 읽어서 Bronze 테이블에 append

2) `spark/jobs/bronze_to_silver.py`
   - 타입 캐스팅, 중복 제거, ts_utc 정규화
   - silver.ticks, silver.dim_contract 생성/갱신

3) `spark/jobs/silver_to_gold_bars.py`
   - 1m 바 생성(OHLC)
   - gold.bars_1m

4) `spark/jobs/gold_features_labels.py`
   - 피처/라벨 생성
   - gold.features_1m, gold.labels_1m

---

## 3) 샘플 실행 커맨드
```bash
spark-submit spark/jobs/ingest_xml_to_bronze.py \
  --input data/sample_xml/202601_20251201_TICK_CALL.xml \
  --table bronze.raw_ticks \
  --cp CALL

spark-submit spark/jobs/ingest_xml_to_bronze.py \
  --input data/sample_xml/202601_20251219_CODE_CALL.xml \
  --table bronze.raw_codes \
  --cp CALL

spark-submit spark/jobs/bronze_to_silver.py \
  --ticks bronze.raw_ticks \
  --codes bronze.raw_codes \
  --out_ticks silver.ticks \
  --out_dim silver.dim_contract

spark-submit spark/jobs/silver_to_gold_bars.py \
  --ticks silver.ticks \
  --out gold.bars_1m \
  --bar_seconds 60

spark-submit spark/jobs/gold_features_labels.py \
  --bars gold.bars_1m \
  --out_features gold.features_1m \
  --out_labels gold.labels_1m
```

---

## 4) 운영 팁
- Bronze는 원본 보존(클렌징 최소화)
- Silver에서 정합성/중복 제거 + 타입 고정
- Gold는 “학습 목적”에 맞춰 만들기(바/피처/라벨)

---

## 5) Structured Streaming (선택)
런타임 상시 실시간이 아니라면 필수 아님.
- 다만, 실시간으로 Bronze를 쌓고 싶다면 Kafka → Spark Structured Streaming → Iceberg append를 고려할 수 있습니다.
