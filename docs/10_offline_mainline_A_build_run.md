# Offline A (기본) 구축/실행 가이드
( Spark + Iceberg + Ray + MLflow )

이 문서는 **샘플 XML(콜/풋 틱 + 코드 2종)**을 Iceberg에 적재하고,
피처/라벨 테이블을 만든 뒤, Ray로 실험을 돌리고 MLflow로 승격까지 가는
“오프라인 공장” 트랙을 **실행 가능 뼈대**로 제공합니다.

> 본 문서는 HFT가 아닌 **분 단위 전략(1m~5m)**을 전제로 합니다.

---

## 1) 준비물

- Docker Desktop 또는 Docker Engine
- Python 3.11+
- Spark 3.5+ (권장)
- Java 17 (Spark용)
- (선택) WSL2 Ubuntu (Windows에서 권장)

---

## 2) docker compose (MinIO + Nessie + MLflow + Redis)

레포 루트의 `docker-compose.yml`를 사용합니다.

### 2.1 실행

```bash
docker compose up -d
docker compose ps
```

### 2.2 서비스 확인

- MinIO Console: http://localhost:9001
- MLflow UI: http://localhost:5000
- Nessie API: http://localhost:19120/api/v2

---

## 3) Iceberg 카탈로그(Nessie) 기본 개념

- Iceberg 테이블은 객체 스토리지(S3/MinIO)에 저장됩니다.
- Nessie는 “카탈로그/버전관리” 역할을 하며 Iceberg 메타데이터를 관리합니다.

---

## 4) Spark 설정 (Iceberg + Nessie + MinIO)

`scripts/01_spark_shell.sh`는 예시입니다.
운영 환경에서는 spark-submit 옵션으로 동일 설정을 주입하세요.

### 4.1 Spark Shell 실행

```bash
bash scripts/01_spark_shell.sh
```

Spark SQL 프롬프트에서 아래를 실행합니다.

---

## 5) Bronze/Silver/Gold 테이블 생성

스키마는 `docs/30_data_schemas.md`와 동일합니다.

### 5.1 네임스페이스 생성

```sql
CREATE NAMESPACE IF NOT EXISTS lakehouse.options;
```

### 5.2 Bronze 테이블(원천 정규화 전)

```sql
CREATE TABLE IF NOT EXISTS lakehouse.options.bronze_ticks (
  src_file STRING,
  side STRING,               -- CALL | PUT
  ymcode STRING,
  code STRING,
  strike INT,
  idate INT,
  itime INT,
  tdate TIMESTAMP,
  tcnt BIGINT,
  c DOUBLE,
  o DOUBLE,
  h DOUBLE,
  l DOUBLE,
  oi DOUBLE,
  ccnt BIGINT,
  ingest_ts TIMESTAMP
) USING iceberg
PARTITIONED BY (days(tdate), side);
```

```sql
CREATE TABLE IF NOT EXISTS lakehouse.options.bronze_codes (
  src_file STRING,
  side STRING,               -- CALL | PUT
  ymcode STRING,
  code STRING,
  lastday INT,
  ingest_ts TIMESTAMP
) USING iceberg
PARTITIONED BY (side, ymcode);
```

### 5.3 Silver (정규화 이벤트/차원)

```sql
CREATE TABLE IF NOT EXISTS lakehouse.options.silver_ticks (
  ymcode STRING,
  side STRING,
  code STRING,
  strike INT,
  ts TIMESTAMP,              -- tdate 표준화
  tcnt BIGINT,
  price DOUBLE,              -- c
  open DOUBLE,
  high DOUBLE,
  low DOUBLE,
  oi DOUBLE,
  ccnt BIGINT,
  trade_date DATE,
  minute_ts TIMESTAMP,       -- 1분 버킷(바 생성용)
  ingest_ts TIMESTAMP
) USING iceberg
PARTITIONED BY (trade_date, side);
```

```sql
CREATE TABLE IF NOT EXISTS lakehouse.options.dim_contract (
  ymcode STRING,
  side STRING,
  code STRING,
  strike INT,
  lastday INT,
  effective_from DATE,
  effective_to DATE
) USING iceberg
PARTITIONED BY (ymcode, side);
```

### 5.4 Gold (바/피처/라벨)

```sql
CREATE TABLE IF NOT EXISTS lakehouse.options.gold_bars_1m (
  ymcode STRING,
  side STRING,
  code STRING,
  strike INT,
  bar_ts TIMESTAMP,          -- 1분 바의 시작 시각
  o DOUBLE,
  h DOUBLE,
  l DOUBLE,
  c DOUBLE,
  v BIGINT,                  -- 거래량(샘플엔 없으니 ccnt 또는 tick수로 proxy)
  tick_count BIGINT,
  oi_last DOUBLE,
  trade_date DATE
) USING iceberg
PARTITIONED BY (trade_date, side);
```

```sql
CREATE TABLE IF NOT EXISTS lakehouse.options.gold_features_1m (
  ymcode STRING,
  side STRING,
  code STRING,
  strike INT,
  asof_ts TIMESTAMP,         -- 피처 기준 시각(바 종료 시각 등)
  f_ret_1 DOUBLE,
  f_ret_5 DOUBLE,
  f_vol_20 DOUBLE,
  f_range_5 DOUBLE,
  f_oi_chg_5 DOUBLE,
  f_spread_proxy DOUBLE,     -- 호가가 없으면 proxy
  f_iv_proxy DOUBLE,         -- IV 없으면 proxy(추후 확장)
  trade_date DATE
) USING iceberg
PARTITIONED BY (trade_date, side);
```

```sql
CREATE TABLE IF NOT EXISTS lakehouse.options.gold_labels_1m (
  ymcode STRING,
  side STRING,
  code STRING,
  strike INT,
  asof_ts TIMESTAMP,
  y_fwd_ret_5 DOUBLE,        -- 5분 후 수익률(예시)
  y_fwd_ret_15 DOUBLE,       -- 15분 후 수익률(예시)
  trade_date DATE
) USING iceberg
PARTITIONED BY (trade_date, side);
```

---

## 6) XML → Bronze 적재 (PySpark)

### 6.0 spark-xml 의존성

이 레포의 XML 적재는 Spark에서 `spark-xml` 패키지를 사용합니다.

- Maven: `com.databricks:spark-xml_2.12:0.17.0`
- `scripts/01_spark_shell.sh`에 포함되어 있습니다.



`python spark_jobs/ingest_xml_to_bronze.py`를 사용합니다.

### 6.1 실행 예시

```bash
export SPARK_MASTER=local[*]
python spark_jobs/ingest_xml_to_bronze.py   --tick-call data/sample_xml/202601_20251201_TICK_CALL.xml   --tick-put  data/sample_xml/202601_20251201_TICK_PUT.xml   --code-call data/sample_xml/202601_20251219_CODE_CALL.xml   --code-put  data/sample_xml/202601_20251219_CODE_PUT.xml
```

---

## 7) Bronze → Silver (정규화/파티션/타입)

```bash
python spark_jobs/etl_bronze_to_silver.py
```

---

## 8) Silver → Gold (바/피처/라벨)

```bash
python spark_jobs/features_silver_to_gold.py --bar-interval 1m
```

---

## 9) 학습/실험 (Ray + LightGBM + MLflow)

> 이 레포는 “뼈대”를 제공합니다. 실제로는
> - 워크포워드 폴드 정의
> - 비용/슬리피지 모델
> - 레짐 분리
> 를 반드시 붙여야 합니다.

```bash
python -m ml.train_lgbm_ray_mlflow   --features-table lakehouse.options.gold_features_1m   --labels-table   lakehouse.options.gold_labels_1m   --mlflow-uri     http://localhost:5000   --experiment     options_lgbm_offlineA
```

---

## 10) 승격(Promotion) 정책(요약)

- MLflow Tracking에 실험(run)을 모두 기록
- 후보 중 상위 N개를 고른 뒤
- 품질 게이트(워크포워드 성과/최악 구간/비용민감도)를 통과한 모델만
  - Registry의 Staging → Production 으로 승격

자세한 체크리스트는 `docs/40_checklist.md` 참고.

