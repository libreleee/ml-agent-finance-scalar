# Spark ETL 코드 골격 (PySpark + Iceberg)

이 문서는 `spark_jobs/`에 포함된 코드의 구조를 설명합니다.

---

## 1) XML 파일 구조

샘플 XML은 공통적으로 다음 형태입니다:

- root: `DocumentElement`
- rowTag:

> XML 로딩은 `spark-xml`(Databricks) 패키지가 필요합니다.

rowTag: 파일마다 다름
  - tick_call 예: `_x0032_02601_20251201_TICK_CALL`
  - tick_put  예: `_x0032_02601_20251201_TICK_PUT`
  - code_call 예: `_x0032_02601_20251219CODE_CALL`
  - code_put  예: `_x0032_02601_20251219CODE_PUT`

tick row는 13개 필드를 포함합니다:
`ymcode, code, strike, idate, itime, tdate, tcnt, c, o, h, l, oi, ccnt`

code row는 3개 필드를 포함합니다:
`ymcode, code, lastday`

---

## 2) spark_jobs 구성

- `ingest_xml_to_bronze.py`
  - XML 파싱 → 타입캐스팅 → bronze_ticks/bronze_codes 적재
- `etl_bronze_to_silver.py`
  - 표준화(ts/minute_ts/trade_date) → silver_ticks
  - code와 join하여 dim_contract 생성(기본)
- `features_silver_to_gold.py`
  - 1분 바 생성(gold_bars_1m)
  - 기본 피처/라벨 생성(gold_features_1m, gold_labels_1m)

---

## 3) Iceberg 카탈로그 연결

SparkSession 생성 시 다음 설정이 필수입니다:

- `spark.sql.catalog.lakehouse=org.apache.iceberg.spark.SparkCatalog`
- `spark.sql.catalog.lakehouse.catalog-impl=org.apache.iceberg.nessie.NessieCatalog`
- `spark.sql.catalog.lakehouse.uri=http://localhost:19120/api/v2`
- `spark.sql.catalog.lakehouse.warehouse=s3a://warehouse/`
- S3A 설정(minio endpoint, key/secret 등)

참고: `scripts/01_spark_shell.sh`에 동일 설정이 들어 있습니다.

---

## 4) “실전 운영”에서의 권장 개선

- 파일 단위 ingest 시:
  - 중복 ingest 방지를 위해 `src_file` + `max(tcnt)` 체크 또는 checksum 기록 테이블 유지
- 타임존:
  - `tdate`는 KST(+09:00)가 포함되어 있으나, Spark 파싱 정책을 고정하세요.
  - 추천: 저장은 UTC로 통일하고, 표시만 KST로 변환
- volume 부재:
  - 샘플 tick에 volume이 없으므로 `tick_count` 또는 `ccnt`로 proxy
  - 실제 운영에서는 거래량/체결수량이 있는 원천을 확보 권장

