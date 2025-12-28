# Lakehouse Tick - 실행 안내서

이 README는 스택을 실행하고 제공된 예제 스크립트로 시각화 흐름을 테스트하는 간단한 단계별 가이드를 제공합니다.

---

## 🎯 시각화 스택 (Visualization Stack) - 빠른 시작

### ⚡ 2분 안에 시작하기

```bash
# 1단계: 시작 가이드 읽기
cat START_HERE.md

# 2단계: 모든 서비스 시작
docker compose up -d

# 3단계: 브라우저에서 접속
# - Superset: http://localhost:8088 (admin/admin)
# - Grafana: http://localhost:3000 (admin/admin)
# - Streamlit: http://localhost:8501
```

### 📚 상세 문서

| 문서 | 설명 | 시간 |
|------|------|------|
| [START_HERE.md](START_HERE.md) | 2분 안에 상황 파악 | 2분 |
| [GETTING_STARTED.md](GETTING_STARTED.md) | 종합 시작 가이드 | 10분 |
| [PHASE_4_EXECUTION_GUIDE.md](PHASE_4_EXECUTION_GUIDE.md) | Phase 4-10 상세 단계 | 1시간+ |
| [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) | 배포 상황 요약 | 5분 |
| [docs/feature/visualization/README.md](docs/feature/visualization/README.md) | 3-Tier 아키텍처 | 15분 |
| [docs/feature/visualization/DEVELOPMENT_CHECKLIST.md](docs/feature/visualization/DEVELOPMENT_CHECKLIST.md) | 202개 체크리스트 (진행 중 참고) | 지속 |

### 🎁 접근 가능한 도구

배포 완료 후:

| 도구 | URL | 계정 | Phase |
|------|-----|------|-------|
| 📊 **Superset** (BI 대시보드) | http://localhost:8088 | admin/admin | 6+ |
| 📈 **Grafana** (모니터링) | http://localhost:3000 | admin/admin | 7+ |
| 🖼️ **Streamlit** (이미지 갤러리) | http://localhost:8501 | (없음) | 8+ |
| 📝 **OpenSearch** (로그) | http://localhost:5601 | admin/Admin@123 | 4+ |
| 🔥 **Prometheus** (메트릭) | http://localhost:9090 | (없음) | 4+ |

---

## 0) 전제 조건

- Docker 및 Docker Compose
- 최소 8GB RAM 및 50GB 이상의 여유 디스크 공간
- 사용해야 하는 포트: 8080, 8088, 3000, 5601, 8501, 9200, 9090, 9333, 8333

## 1) 환경 (.env)

기본 개발용 값은 이미 `.env`에 포함되어 있습니다:

```bash
SUPERSET_SECRET_KEY=your-super-secret-key
SUPERSET_ADMIN_USER=admin
SUPERSET_ADMIN_PASSWORD=admin
GRAFANA_PASSWORD=admin
OPENSEARCH_PASSWORD=Admin@123
```

프로덕션에서는 배포 전에 이 값을 적절히 변경하세요.

SUPERSET_SECRET_KEY 참고:
- 외부 서버에서 발급받는 키가 아닙니다.
- Superset가 세션/쿠키 서명에 사용하는 로컬 애플리케이션 시크릿입니다.
- 운영 환경에서는 충분히 긴 랜덤 값으로 생성해 사용하세요.

## 2) 핵심 서비스 시작 (데이터 + Trino 최소 구성)

```bash
docker compose up -d \
  seaweedfs-master seaweedfs-volume seaweedfs-filer seaweedfs-s3 \
  postgres hive-metastore trino
```
docker compose up seaweedfs-master seaweedfs-volume seaweedfs-filer seaweedfs-s3 postgres hive-metastore trino


## 3) 시각화 서비스 시작 (선택 사항이지만 권장)

```bash
docker compose up -d \
  superset-db superset-redis superset \
  opensearch opensearch-dashboards prometheus node-exporter grafana \
  streamlit
```

> **더 자세한 설명**: [PHASE_4_EXECUTION_GUIDE.md](PHASE_4_EXECUTION_GUIDE.md) 참고



## 4) 샘플 데이터 적재 (기존 스크립트 사용)

가상환경을 활성화한 뒤(필요한 경우), 다음을 실행하세요:

```bash
python python/fspark_raw_examples.py
```

이 스크립트는 다음을 작성합니다:
- 원시 JSON 로그: `s3a://lakehouse/raw/logs/...`
- Iceberg 테이블: Hive 메타스토어의 `hive_prod.logs_db.raw_logs`
- 샘플 파일: `s3a://lakehouse/raw/images/...`

## 5) Trino로 확인 (CLI)

```bash
docker compose exec trino trino --server http://localhost:8080
```

```sql
SHOW SCHEMAS FROM iceberg;
SHOW TABLES FROM iceberg.logs_db;
SELECT * FROM iceberg.logs_db.raw_logs LIMIT 10;
```

## 6) Superset 빠른 점검

- 접속: http://localhost:8088 (admin/admin)
- DB 연결 추가:
  - Database: Trino
  - Connection URI: `trino://user@trino:8080/hive_prod`
- 데이터셋 생성: schema `option_ticks_db`, table `bronze_option_ticks`
- 예시 차트 쿼리:

```sql
SELECT symbol, COUNT(*) AS cnt, AVG(last_price) AS avg_price
FROM hive_prod.option_ticks_db.bronze_option_ticks
GROUP BY symbol
ORDER BY cnt DESC;
```

> **Tier 1 (BI 대시보드) 상세 가이드**: [docs/feature/visualization/01-tier1-superset-trino-structured.md](docs/feature/visualization/01-tier1-superset-trino-structured.md)

## 7) Streamlit 빠른 점검

- 접속: http://localhost:8501
- 기능:
  - **Gallery**: 이미지 메타데이터 기반 이미지 갤러리
  - **Search**: 메타데이터 검색
  - **Statistics**: 태그별 통계 및 크기 분포

> **Tier 3 (이미지 갤러리) 상세 가이드**: [docs/feature/visualization/03-tier3-streamlit-unstructured.md](docs/feature/visualization/03-tier3-streamlit-unstructured.md)

참고: Streamlit 페이지는 `hive_prod.media_db.image_metadata` 테이블을 사용합니다.
다른 데이터셋을 시각화하려면 [streamlit-app/pages/](streamlit-app/pages/)의 페이지를 수정하세요.

## 8) Grafana / OpenSearch / Prometheus (Tier 2: 실시간 모니터링)

### Grafana (모니터링 대시보드)
- 접속: http://localhost:3000 (admin/admin)
- 기능:
  - **Prometheus 데이터 소스**: 시스템 메트릭 (CPU, 메모리, 디스크)
  - **OpenSearch 데이터 소스**: 로그 탐색 및 분석
  - **대시보드**: 실시간 모니터링

> **Tier 2 (모니터링) 상세 가이드**: [docs/feature/visualization/02-tier2-grafana-opensearch-semistructured.md](docs/feature/visualization/02-tier2-grafana-opensearch-semistructured.md)

### OpenSearch Dashboards (로그 분석)
- 접속: http://localhost:5601 (admin/Admin@123)
- 기능:
  - **로그 스트림**: 시스템, 애플리케이션 로그 수집
  - **Discover**: 로그 검색 및 필터링
  - **대시보드**: 로그 기반 시각화

### Prometheus (메트릭 수집)
- 접속: http://localhost:9090
- 기능:
  - **Node Exporter**: 시스템 메트릭 (CPU, 메모리, 디스크, 네트워크)
  - **수동 쿼리**: Prometheus UI에서 PromQL 쿼리 실행

**참고**: 로그 수집은 기본적으로 완전히 연결되어 있지 않습니다. 로그를 완벽히 시각화하려면 로그 수집기(Fluent Bit / Vector 등)를 추가하고 인덱스 패턴을 설정하세요. [PHASE_4_EXECUTION_GUIDE.md](PHASE_4_EXECUTION_GUIDE.md)의 Phase 7 참고.

## 9) 서비스 중지

```bash
docker compose down
```

---

## 📚 시각화 스택 종합 가이드

### 3-Tier 아키텍처

이 프로젝트는 데이터 유형별로 최적화된 3개의 시각화 Tier를 제공합니다:

| Tier | 데이터 유형 | 주 도구 | 사용 사례 |
|------|-----------|--------|---------|
| **Tier 1** | 정형 (Structured) | Superset + Trino | BI 분석, KPI 추적, 경영 대시보드 |
| **Tier 2** | 반정형 (Semi-structured) | Grafana + OpenSearch + Prometheus | 실시간 모니터링, 로그 분석, 알림 |
| **Tier 3** | 비정형 (Unstructured) | Streamlit + PyIceberg | 이미지 탐색, 메타데이터 검색, 통계 |

### 🚀 배포 프로세스

총 10개 Phase로 구성:
- **Phase 0-3** (준비): ✅ 완료 (docker-compose, 설정, 코드)
- **Phase 4-10** (실행): 🚀 준비 완료

자세한 배포 단계: [PHASE_4_EXECUTION_GUIDE.md](PHASE_4_EXECUTION_GUIDE.md)

### 📋 체크리스트

모든 구현 단계를 추적할 수 있는 202개 항목의 체크리스트:
[docs/feature/visualization/DEVELOPMENT_CHECKLIST.md](docs/feature/visualization/DEVELOPMENT_CHECKLIST.md)

### 💾 데이터 구조

```
Bronze Layer (원본 데이터):
├─ 정형: hive_prod.option_ticks_db.bronze_option_ticks
├─ 반정형: hive_prod.logs_db.raw_logs (JSON)
└─ 비정형: s3a://lakehouse/raw/images/{date}/*.png

Iceberg Metadata:
├─ hive_prod.option_ticks_db.bronze_option_ticks
├─ hive_prod.logs_db.raw_logs
└─ hive_prod.media_db.image_metadata (이미지 메타데이터)
```

### 🔧 커스터마이징

#### 다른 데이터셋 시각화하기

1. **Superset**: [docs/feature/visualization/01-tier1-superset-trino-structured.md](docs/feature/visualization/01-tier1-superset-trino-structured.md) 참고
2. **Streamlit**: [streamlit-app/pages/](streamlit-app/pages/) 수정
3. **Grafana**: [config/grafana/provisioning/dashboards/](config/grafana/provisioning/dashboards/) 수정

#### 비밀번호 변경 (프로덕션)

`.env` 파일에서:
```bash
SUPERSET_SECRET_KEY=<strong-random-key>
SUPERSET_ADMIN_PASSWORD=<strong-password>
GRAFANA_PASSWORD=<strong-password>
OPENSEARCH_PASSWORD=<strong-password>
```

### 📖 추가 리소스

- [START_HERE.md](START_HERE.md) - 2분 안내
- [GETTING_STARTED.md](GETTING_STARTED.md) - 10분 가이드
- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) - 배포 상황
- [docs/feature/visualization/README.md](docs/feature/visualization/README.md) - 3-Tier 상세 설명
- [docs/feature/visualization/QUICK_REFERENCE.md](docs/feature/visualization/QUICK_REFERENCE.md) - 빠른 참조

---

## 📊 배포 후 접근 가능한 도구

| 도구 | URL | 계정 | 시간 |
|------|-----|------|------|
| 📊 **Superset** | http://localhost:8088 | admin/admin | Phase 6 이후 |
| 📈 **Grafana** | http://localhost:3000 | admin/admin | Phase 7 이후 |
| 🖼️ **Streamlit** | http://localhost:8501 | (없음) | Phase 8 이후 |
| 📝 **OpenSearch** | http://localhost:5601 | admin/Admin@123 | Phase 4 이후 |
| 🔥 **Prometheus** | http://localhost:9090 | (없음) | Phase 4 이후 |

---

## 🧭 홈 접속 방법

1. **Superset 접속**: http://localhost:8088  
   - 계정: `admin` / `admin`  
   - Trino 연결: **Settings → Database Connections → + Database → SQLAlchemy URI**  
     - URI: `trino://user@trino:8080/iceberg`
2. **Grafana 접속**: http://localhost:3000 (admin/admin)
3. **OpenSearch Dashboards 접속**: http://localhost:5601/app/home (admin/Admin@123)
4. **Streamlit 접속**: http://localhost:8501
5. **Prometheus 접속**: http://localhost:9090

**모든 준비가 완료되었습니다!** 지금 바로 [START_HERE.md](START_HERE.md)를 읽고 시작하세요. 🚀

---

## 🤖 MLOps 스택 (MLflow + Airflow)

### ⚡ MLOps 서비스 실행

MLOps 스택은 별도의 Compose 파일로 관리됩니다.

```bash
# MLOps 서비스 시작 (MLflow + Airflow)
docker compose -f docker-compose-mlops.yml up -d

# 서비스 상태 확인
docker compose -f docker-compose-mlops.yml ps

# 로그 확인
docker compose -f docker-compose-mlops.yml logs -f mlflow
docker compose -f docker-compose-mlops.yml logs -f airflow-webserver

# MLOps 서비스 중지
docker compose -f docker-compose-mlops.yml down

# 볼륨까지 완전 삭제
docker compose -f docker-compose-mlops.yml down -v
```

### 🌐 MLOps 접속 URL

| 도구 | URL | 계정 | 설명 |
|------|-----|------|------|
| 🧪 **MLflow** | http://localhost:5000 | (없음) | 실험 추적 & 모델 레지스트리 |
| 🔄 **Airflow** | http://localhost:8082 | admin/admin | 워크플로우 오케스트레이션 |

### 🔧 자동 시작 설정 (Docker Restart Policy)

MLOps 컨테이너는 `restart: unless-stopped` 정책이 설정되어 있습니다.
재부팅 시 Docker 서비스가 시작되면 자동으로 컨테이너가 시작됩니다.

#### 현재 설정 확인

```bash
# MLflow restart policy 확인
docker inspect mlflow --format='{{.HostConfig.RestartPolicy.Name}}'

# Airflow 컨테이너들 restart policy 확인
docker inspect airflow-webserver --format='{{.HostConfig.RestartPolicy.Name}}'
docker inspect airflow-scheduler --format='{{.HostConfig.RestartPolicy.Name}}'
docker inspect airflow-worker --format='{{.HostConfig.RestartPolicy.Name}}'
```

#### 자동 시작 비활성화 (수동 시작으로 변경)

```bash
# 모든 MLOps 컨테이너의 restart policy를 'no'로 변경
docker update --restart=no mlflow
docker update --restart=no airflow-webserver
docker update --restart=no airflow-scheduler
docker update --restart=no airflow-worker
docker update --restart=no airflow-postgres
docker update --restart=no airflow-redis

# 확인
docker inspect mlflow --format='{{.HostConfig.RestartPolicy.Name}}'
```

#### 자동 시작 다시 활성화

```bash
# restart policy를 'unless-stopped'로 변경
docker update --restart=unless-stopped mlflow
docker update --restart=unless-stopped airflow-webserver
docker update --restart=unless-stopped airflow-scheduler
docker update --restart=unless-stopped airflow-worker
docker update --restart=unless-stopped airflow-postgres
docker update --restart=unless-stopped airflow-redis

# 확인
docker inspect mlflow --format='{{.HostConfig.RestartPolicy.Name}}'
```

#### Restart Policy 옵션 설명

| 정책 | 설명 |
|------|------|
| `no` | 자동 재시작 안 함 (수동 시작만) |
| `always` | 항상 자동 재시작 (docker stop 해도 재부팅 시 시작) |
| `unless-stopped` | docker stop 하기 전까지 자동 재시작 (현재 설정) |
| `on-failure` | 오류로 종료될 때만 재시작 |

#### ⚠️ 재부팅 시 주의사항

재부팅 후 자동 시작 시 `depends_on`이 무시되어 컨테이너가 병렬로 시작됩니다.

**발생 가능한 현상**:
- 로그에 연결 실패 에러가 일시적으로 발생할 수 있습니다
- 모든 서비스가 준비되는 데 2-3분 소요될 수 있습니다
- healthcheck와 restart policy가 자동으로 복구합니다

**완전한 순서 보장이 필요하면**:
```bash
# 1. restart policy를 'no'로 변경 (자동 시작 비활성화)
docker update --restart=no mlflow airflow-webserver airflow-scheduler airflow-worker airflow-postgres airflow-redis

# 2. 재부팅 후 수동으로 올바른 순서대로 시작
# (아래 "올바른 시작 순서" 섹션 참고)
```

### 📊 DAG 실행 예제

```bash
# Airflow DAG 목록 확인
docker exec airflow-scheduler airflow dags list

# ML Pipeline DAG 수동 실행
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# DAG 실행 상태 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end

# Scheduler 로그 확인
docker logs airflow-scheduler --tail 100

# Worker 로그 확인 (실제 Task 실행 로그)
docker logs airflow-worker --tail 100

# 특정 Task 상태 확인
docker exec airflow-scheduler airflow tasks state ml_pipeline_end_to_end raw_to_bronze <execution_date>
```

### 💡 MLOps 통합 워크플로우

```
[1] Airflow DAG 실행
    └─ 데이터 파이프라인: RAW → Bronze → Silver → Gold

[2] MLflow 실험 추적
    └─ Feature Engineering → Model Training → Evaluation

[3] MLflow Model Registry
    └─ 검증된 모델을 Production으로 등록

[4] 스케줄링
    └─ Airflow로 매일 자동 재학습 (schedule=timedelta(days=1))
```

### 🔍 트러블슈팅

#### MLflow가 S3(SeaweedFS)에 연결 안 될 때:
```bash
# SeaweedFS S3 서비스 확인
docker ps | grep seaweedfs

# MLflow 환경변수 확인
docker exec mlflow env | grep MLFLOW

# MLflow 재시작
docker compose -f docker-compose-mlops.yml restart mlflow
```

#### Airflow DAG가 인식되지 않을 때:
```bash
# DAG 파일 존재 확인
ls -la /home/i/work/ai/lakehouse-tick/dags/

# Scheduler 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-scheduler | grep ERROR

# Scheduler 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler
```

---




장 순서 정리:
README.md에 이 순서를 명확히 추가해야 할까요?

## 🚀 올바른 시작 순서

### 1️⃣ 인프라 서비스 (필수) 핵심 서비스 시작 (데이터 + Trino 최소 구성)
docker compose up -d seaweedfs-master seaweedfs-volume seaweedfs-filer seaweedfs-s3 postgres hive-metastore trino spark-iceberg

### 2️⃣ 쿼리 엔진 - 위에서 빼고 별도실행도 가능 trino(옵션)
docker compose up -d trino

### 3️⃣ 시각화 서비스 (선택)
docker compose up -d superset-db superset-redis superset opensearch opensearch-dashboards prometheus node-exporter grafana streamlit


### 4️⃣ MLOps 스택 (선택)
docker compose -f docker-compose-mlops.yml up -d


---

## 🛑 올바른 종료 순서 (시작의 역순)

### 4️⃣ MLOps 스택 종료 (먼저!)
```bash
docker compose -f docker-compose-mlops.yml down
```

### 3️⃣ 시각화 서비스 종료
```bash
docker compose stop streamlit grafana node-exporter prometheus \
  opensearch-dashboards opensearch superset superset-redis superset-db
```

### 2️⃣ 쿼리 엔진 종료
```bash
docker compose stop trino
```

### 1️⃣ 인프라 서비스 종료 (마지막!)
```bash
docker compose stop hive-metastore postgres \
  seaweedfs-s3 seaweedfs-filer seaweedfs-volume seaweedfs-master
```

### 🔥 전체 종료 (빠른 방법)
```bash
# 모든 서비스 종료 (권장)
docker compose -f docker-compose-mlops.yml down
docker compose down

# 볼륨까지 완전 삭제 (주의! 데이터 손실)
docker compose -f docker-compose-mlops.yml down -v
docker compose down -v
```

### 🔄 개별 서비스 재시작
```bash
# MLflow만 재시작
docker compose -f docker-compose-mlops.yml restart mlflow

# Airflow Scheduler만 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler

# Trino만 재시작
docker compose restart trino

# SeaweedFS S3만 재시작
docker compose restart seaweedfs-s3
```

---

## ⚠️ 순서가 중요한 이유

### 시작 순서:
```
인프라 → 쿼리 엔진 → 시각화 → MLOps
(의존성이 없는 것부터 → 의존성이 있는 것)
```

### 종료 순서:
```
MLOps → 시각화 → 쿼리 엔진 → 인프라
(의존하는 것부터 → 의존성 제공자)
```

**이유**:
- MLOps가 Trino에 연결되어 있는 상태에서 Trino를 먼저 종료하면 에러 발생
- Trino가 Hive Metastore를 사용 중일 때 Metastore 먼저 종료하면 연결 끊김

---



## 🚀 올바른 시작 순서

### 1️⃣ 인프라 서비스 (필수) 핵심 서비스 시작 (데이터 + Trino 최소 구성)
docker compose up seaweedfs-master seaweedfs-volume seaweedfs-filer seaweedfs-s3 postgres hive-metastore trino spark-iceberg

### 2️⃣ 쿼리 엔진 - 위에서 빼고 별도실행도 가능 trino(옵션)
docker compose up -d trino

### 3️⃣ 시각화 서비스 (선택)
docker compose up -d superset-db superset-redis superset opensearch opensearch-dashboards prometheus node-exporter grafana streamlit


### 4️⃣ MLOps 스택 (선택)
docker compose -f docker-compose-mlops.yml up -d

