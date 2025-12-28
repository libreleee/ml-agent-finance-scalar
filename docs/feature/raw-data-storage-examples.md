# 데이터 레이크: 정형 / 반정형 / 비정형 저장 예제 및 운영 가이드 ✅

## 요약
- 이 문서는 본 프로젝트(SeaweedFS S3 게이트웨이 + Apache Iceberg + Spark)를 기준으로 **정형(테이블)**, **반정형(JSON 로그)**, **비정형(이미지/바이너리)** 데이터를 저장하고 처리하는 예제와 실행·문제해결 팁을 제공합니다. 
- 예제 스크립트:
  - `python/fspark.py` — 정형(테이블) 적재 예제
  - `python/fspark_raw_examples.py` — 반정형(JSON) + 비정형(바이너리) 예제

---

## 아키텍처(간단) 🔧
- 저장: SeaweedFS S3 게이트웨이 (endpoint: `http://localhost:8333`)를 `s3a://lakehouse`로 사용
- 테이블 관리: Apache Iceberg (`hive_prod` 카탈로그)
- 처리: Apache Spark (PySpark)

---

## 실행 전 필수 확인 ✅
1. 가상환경 활성화 및 파이썬 경로 일치
   ```bash
   source /home/i/work/ai/.venv/bin/activate
   export PYSPARK_PYTHON=/home/i/work/ai/.venv/bin/python
   export PYSPARK_DRIVER_PYTHON=/home/i/work/ai/.venv/bin/python
   ```
2. 스크립트 내 S3 접근키(테스트용)는 `seaweedfs_access_key / seaweedfs_secret_key`로 설정되어 있습니다. 프로덕션에서는 비밀관리 사용 권장.

---

## 1) 정형 데이터: `python/fspark.py` (예제)
- 목적: Iceberg 테이블(`hive_prod.option_ticks_db.bronze_option_ticks`) 생성 및 샘플 데이터 append
- 실행
  ```bash
  /home/i/work/ai/.venv/bin/python python/fspark.py
  ```
- 기대 결과: 테이블 생성 후 샘플 행이 적재되고, `SELECT * FROM hive_prod.option_ticks_db.bronze_option_ticks`로 확인 가능

---

## 2) 반정형 데이터: JSON 로그 예제 (원본 보존 + Iceberg 적재)
- 스크립트: `python/fspark_raw_examples.py` (부분 요약)
  - 원본 JSON을 `s3a://lakehouse/raw/logs/date=YYYY-MM-DD/`에 저장
  - 동일 데이터를 Iceberg 테이블 `hive_prod.logs_db.raw_logs`(bronze)에 적재
- 실행
  ```bash
  /home/i/work/ai/.venv/bin/python python/fspark_raw_examples.py
  ```
- 활용 팁: 원본 JSON은 **원본 보관(raw)**, 분석·조회용은 Parquet/ Iceberg로 변환하여 사용(성능 향상)

---

## 3) 비정형 데이터: 이미지/바이너리 파일 저장 예제
- 목표: 파일(이미지, 오디오 등)을 원본 그대로 S3 경로에 저장
- 구현(스크립트 예시): Hadoop `FileSystem.get(URI, conf)`로 S3A FS를 얻어 파일을 직접 쓰는 방식 사용
- 예시 경로: `s3a://lakehouse/raw/images/{date}/sample.txt` (샘플은 바이너리 텍스트)

---

## 문제 해결(주요 케이스) ⚠️
- PySpark Worker/Driver Python 버전 불일치
  - 에러: `[PYTHON_VERSION_MISMATCH]` → 워커와 드라이버의 **마이너 버전**이 달라 발생
  - 해결: `PYSPARK_PYTHON`/`PYSPARK_DRIVER_PYTHON`을 동일한 가상환경 파이썬으로 설정

- S3A 설정(시간 값 format) 관련 `NumberFormatException`
  - 원인: `60s`, `24h`처럼 단위가 있는 문자열이 숫자만 기대되는 곳에 들어감
  - 해결: `spark` 설정에서 숫자(예: `60000`)로 덮어쓰기

- Iceberg `S3FileIO` / AWS SDK 관련 `NoClassDefFoundError`
  - 해결: `spark.jars.packages`에 AWS SDK 의존성(예: `software.amazon.awssdk:bundle`, `com.amazonaws:aws-java-sdk-bundle`) 추가

- S3A로 바이너리 파일 저장 시 `Wrong FS` 에러
  - 원인: FileSystem을 초기화할 때 URI를 전달하지 않음
  - 해결: `FileSystem.get(URI(image_s3_path), conf)` 사용

- Iceberg 테이블 생성 시 `version-hint.text` 존재하지 않는 경고
  - 설명: 신규 테이블이거나 메타데이터 누락 시 발생 (경고로 무시 가능하지만 정확성 확인 필요)

---

## 권장 운영 방안 / 다음 단계 💡
- 구조: `raw/`(원본) → `bronze/`(정제 전) → `silver/`(클린/UUID 변환) → `gold/`(비즈니스용 집계) 계층 운영
- 자동화: Airflow / cron / Kubernetes CronJob으로 ingestion 파이프라인 스케줄링
- 거버넌스: 메타데이터 카탈로그(Glue/Hive Metastore), 접근 제어, 암호화 도입
- 포맷 추천: 원본은 유지, 분석용은 Parquet + Iceberg를 권장

---

## 참고 코드 위치
- `python/fspark.py` (정형 예제)
- `python/fspark_raw_examples.py` (반정형 + 비정형 예제)

---

문서에 추가하거나 예제 보완(예: Parquet 변환 샘플, Airflow DAG 파일 추가)을 원하시면 알려 주세요.