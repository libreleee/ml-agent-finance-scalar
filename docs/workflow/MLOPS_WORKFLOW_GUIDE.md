# MLOps 워크플로우 가이드

## 📋 목차

1. [개요](#개요)
2. [시작하기](#시작하기)
3. [MLOps 스택 실행](#mlops-스택-실행)
4. [Airflow 사용법](#airflow-사용법)
5. [MLflow 사용법](#mlflow-사용법)
6. [DAG 작성 가이드](#dag-작성-가이드)
7. [ML 파이프라인 예제](#ml-파이프라인-예제)
8. [모니터링 및 디버깅](#모니터링-및-디버깅)
9. [트러블슈팅](#트러블슈팅)

---

## 개요

### 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     MLOps Workflow Stack                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │   Airflow    │────────▶│   MLflow     │                      │
│  │  (Workflow)  │         │ (Tracking)   │                      │
│  └──────────────┘         └──────────────┘                      │
│         │                         │                              │
│         │                         │                              │
│         ▼                         ▼                              │
│  ┌──────────────┐         ┌──────────────┐                      │
│  │    Trino     │         │  SeaweedFS   │                      │
│  │   (Query)    │         │   (S3 API)   │                      │
│  └──────────────┘         └──────────────┘                      │
│         │                         │                              │
│         └─────────┬───────────────┘                              │
│                   ▼                                              │
│           ┌──────────────┐                                       │
│           │   Iceberg    │                                       │
│           │  Data Lake   │                                       │
│           └──────────────┘                                       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 주요 컴포넌트

| 컴포넌트 | 역할 | 포트 |
|---------|------|------|
| **Airflow Webserver** | DAG 관리 UI | 8082 |
| **Airflow Scheduler** | DAG 스케줄링 | - |
| **Airflow Worker** | Task 실행 | - |
| **MLflow** | 실험 추적 & 모델 레지스트리 | 5000 |
| **PostgreSQL** | Airflow 메타데이터 | - |
| **Redis** | Celery 메시지 브로커 | 6379 |

---

## 시작하기

### 필수 요구사항

- Docker 및 Docker Compose 설치
- 최소 8GB RAM
- 최소 20GB 디스크 공간
- 기존 Lakehouse 인프라 실행 중

### 접속 정보

| 서비스 | URL | 계정 |
|--------|-----|------|
| Airflow UI | http://localhost:8082 | admin / admin |
| MLflow UI | http://localhost:5000 | (인증 없음) |

---

## MLOps 스택 실행

### 1️⃣ 전체 스택 시작

```bash
cd /home/i/work/ai/lakehouse-tick

# 1단계: Lakehouse 인프라 확인 (이미 실행 중이어야 함)
docker compose ps

# 2단계: MLOps 스택 시작
docker compose -f docker-compose-mlops.yml up -d

# 3단계: 상태 확인
docker compose -f docker-compose-mlops.yml ps
```

**예상 출력**:
```
NAME                    STATUS              PORTS
airflow-postgres        Up (healthy)        5432/tcp
airflow-redis           Up (healthy)        0.0.0.0:6379->6379/tcp
airflow-scheduler       Up (healthy)        8080/tcp
airflow-webserver       Up (healthy)        0.0.0.0:8082->8080/tcp
airflow-worker          Up (healthy)        8080/tcp
mlflow                  Up (healthy)        0.0.0.0:5000->5000/tcp
```

### 2️⃣ 서비스 상태 확인

```bash
# 헬스체크
curl http://localhost:5000/health  # MLflow
curl http://localhost:8082/health  # Airflow

# 로그 확인
docker compose -f docker-compose-mlops.yml logs -f mlflow
docker compose -f docker-compose-mlops.yml logs -f airflow-scheduler
```

### 3️⃣ 서비스 중지

```bash
# MLOps 스택만 중지 (데이터 유지)
docker compose -f docker-compose-mlops.yml stop

# MLOps 스택 완전 제거 (데이터 보존)
docker compose -f docker-compose-mlops.yml down

# MLOps 스택 완전 제거 (데이터 삭제)
docker compose -f docker-compose-mlops.yml down -v
```

---

## Airflow 사용법

### UI 접속

1. 브라우저에서 http://localhost:8082 접속
2. 로그인: `admin` / `admin`

### DAG 관리

#### DAG 목록 확인

```bash
docker exec airflow-scheduler airflow dags list
```

#### DAG 활성화/비활성화

**UI에서**:
1. DAGs 페이지 접속
2. DAG 옆의 토글 스위치 클릭

**CLI에서**:
```bash
# 활성화
docker exec airflow-scheduler airflow dags unpause ml_pipeline_end_to_end

# 비활성화
docker exec airflow-scheduler airflow dags pause ml_pipeline_end_to_end
```

#### DAG 수동 실행

**UI에서**:
1. DAG 이름 클릭
2. 우측 상단 "Trigger DAG" 버튼 클릭

**CLI에서**:
```bash
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end
```

#### DAG 실행 이력 확인

```bash
# 최근 실행 이력
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end

# 특정 실행의 Task 상태
docker exec airflow-scheduler airflow tasks states-for-dag-run \
  ml_pipeline_end_to_end \
  manual__2025-12-25T15:12:37+00:00
```

### Task 관리

#### Task 로그 확인

**UI에서**:
1. DAG 실행 클릭
2. Task 클릭
3. "Log" 탭 선택

**CLI에서**:
```bash
docker exec airflow-scheduler airflow tasks logs \
  ml_pipeline_end_to_end \
  raw_to_bronze \
  2025-12-25
```

#### Task 재실행

**UI에서**:
1. 실패한 Task 클릭
2. "Clear" 버튼 클릭

**CLI에서**:
```bash
docker exec airflow-scheduler airflow tasks clear \
  ml_pipeline_end_to_end \
  --task-regex "raw_to_bronze" \
  --start-date 2025-12-25 \
  --end-date 2025-12-25
```

### 사용자 관리

#### 새 사용자 추가

```bash
docker exec airflow-webserver airflow users create \
  --username data_analyst \
  --firstname Data \
  --lastname Analyst \
  --role Viewer \
  --email analyst@example.com \
  --password analyst123
```

#### 사용자 역할

| 역할 | 권한 |
|------|------|
| **Admin** | 모든 권한 |
| **Op** | DAG 실행/중지 |
| **Viewer** | 읽기 전용 |
| **User** | DAG 실행만 가능 |

---

## MLflow 사용법

### UI 접속

브라우저에서 http://localhost:5000 접속

### 실험 관리

#### 실험 목록 확인

**UI에서**: 좌측 사이드바에서 "Experiments" 확인

**CLI에서**:
```bash
curl -s "http://localhost:5000/api/2.0/mlflow/experiments/search?max_results=100"
```

#### 실험 생성

**Python 코드**:
```python
import mlflow

mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("my-experiment")

with mlflow.start_run():
    mlflow.log_param("learning_rate", 0.01)
    mlflow.log_metric("accuracy", 0.95)
```

### 모델 관리

#### 모델 로깅

```python
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier

# 모델 학습
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# MLflow에 로깅
with mlflow.start_run():
    mlflow.log_param("n_estimators", 100)
    mlflow.sklearn.log_model(model, "model")
```

#### 모델 레지스트리에 등록

```python
from mlflow.tracking import MlflowClient

client = MlflowClient("http://mlflow:5000")

# 모델 등록
model_uri = f"runs:/{run_id}/model"
model_version = mlflow.register_model(model_uri, "my-model")

# Production으로 전환
client.transition_model_version_stage(
    name="my-model",
    version=model_version.version,
    stage="Production"
)
```

#### Production 모델 로드

```python
import mlflow.sklearn

model = mlflow.sklearn.load_model("models:/my-model/Production")
predictions = model.predict(X_test)
```

---

## DAG 작성 가이드

### DAG 파일 위치

```
/home/i/work/ai/lakehouse-tick/
└── dags/
    ├── ml_pipeline_dag.py          # 메인 DAG
    ├── data_ingestion_dag.py       # 데이터 수집 DAG
    └── scripts/
        ├── bronze_layer.py         # Bronze 레이어 스크립트
        ├── silver_layer.py         # Silver 레이어 스크립트
        └── gold_layer.py           # Gold 레이어 스크립트
```

### 기본 DAG 구조

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

# DAG 기본 설정
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# DAG 정의
dag = DAG(
    'my_dag',
    default_args=default_args,
    description='My first DAG',
    schedule_interval='0 2 * * *',  # 매일 02:00
    start_date=datetime(2025, 12, 25),
    catchup=False,
    tags=['example'],
)

# Task 함수
def my_task(**context):
    print("Hello from Airflow!")
    return "Success"

# Task 정의
task1 = PythonOperator(
    task_id='my_task',
    python_callable=my_task,
    dag=dag,
)
```

### Task 의존성 정의

```python
# 순차 실행
task1 >> task2 >> task3

# 병렬 실행 후 합류
task1 >> [task2, task3] >> task4

# 복잡한 의존성
(task1 >> task2) & (task3 >> task4) >> task5
```

### MLflow 통합

```python
from airflow.operators.python import PythonOperator
import mlflow

def train_model(**context):
    mlflow.set_tracking_uri("http://mlflow:5000")
    mlflow.set_experiment("my-experiment")

    with mlflow.start_run(run_name=context['task_instance'].task_id):
        # 파라미터 로깅
        mlflow.log_param("dag_id", context['dag'].dag_id)
        mlflow.log_param("execution_date", str(context['execution_date']))

        # 모델 학습
        accuracy = 0.95

        # 메트릭 로깅
        mlflow.log_metric("accuracy", accuracy)

        return accuracy

train_task = PythonOperator(
    task_id='train_model',
    python_callable=train_model,
    dag=dag,
)
```

### Trino 쿼리 실행

```python
from airflow.providers.trino.operators.trino import TrinoOperator

query_task = TrinoOperator(
    task_id='run_query',
    trino_conn_id='trino_default',
    sql="""
        SELECT symbol, AVG(last_price) as avg_price
        FROM hive_prod.option_ticks_db.bronze_option_ticks
        WHERE DATE(timestamp) = CURRENT_DATE - INTERVAL '1' DAY
        GROUP BY symbol
    """,
    dag=dag,
)
```

---

## ML 파이프라인 예제

### End-to-End ML 파이프라인

이미 작성된 [dags/ml_pipeline_dag.py](../../dags/ml_pipeline_dag.py) 파일을 참조하세요.

파이프라인 단계:

```
1. raw_to_bronze        → 원시 데이터 수집
2. bronze_to_silver     → 데이터 정제
3. silver_to_gold       → 비즈니스 로직 적용
4. feature_engineering  → ML 피처 생성
5. model_training       → 모델 학습 (MLflow 로깅)
6. model_evaluation     → 모델 평가
7. model_registry       → MLflow 모델 레지스트리 등록
```

### 실행 방법

```bash
# 1. DAG 활성화
docker exec airflow-scheduler airflow dags unpause ml_pipeline_end_to_end

# 2. 수동 실행
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# 3. 실행 상태 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end
```

### 실행 결과 확인

**Airflow UI**:
1. http://localhost:8082 접속
2. `ml_pipeline_end_to_end` DAG 클릭
3. Graph View에서 실행 상태 확인

**MLflow UI**:
1. http://localhost:5000 접속
2. "lakehouse_ml_pipeline" 실험 클릭
3. 각 Run의 파라미터 및 메트릭 확인

---

## 모니터링 및 디버깅

### 로그 확인

#### 실시간 로그 모니터링

```bash
# 전체 로그
docker compose -f docker-compose-mlops.yml logs -f

# 특정 서비스
docker compose -f docker-compose-mlops.yml logs -f airflow-scheduler
docker compose -f docker-compose-mlops.yml logs -f airflow-worker
docker compose -f docker-compose-mlops.yml logs -f mlflow
```

#### 로그 파일 위치

```
/home/i/work/ai/lakehouse-tick/
└── logs/
    ├── airflow/
    │   ├── scheduler/
    │   │   └── 2025-12-25/
    │   │       └── dag_processor_manager.log
    │   └── dag_id=ml_pipeline_end_to_end/
    │       └── run_id=manual__2025-12-25T15:12:37+00:00/
    │           └── task_id=raw_to_bronze/
    └── mlflow/
```

### 리소스 모니터링

```bash
# 실시간 리소스 사용률
docker stats mlflow airflow-webserver airflow-scheduler airflow-worker

# 디스크 사용량
docker system df -v | grep -E 'mlflow|airflow'
```

### 성능 메트릭

#### Airflow 메트릭

```bash
# 실행 중인 Task 수
docker exec airflow-scheduler airflow dags list-runs --state running

# 실패한 Task 수
docker exec airflow-scheduler airflow dags list-runs --state failed
```

#### MLflow 메트릭

```bash
# 실험 수
curl -s "http://localhost:5000/api/2.0/mlflow/experiments/search?max_results=100" | grep -c experiment_id

# Run 수
curl -s "http://localhost:5000/api/2.0/mlflow/runs/search?max_results=100" | grep -c run_id
```

---

## 트러블슈팅

### 문제 1: DAG가 인식되지 않음

**증상**: Airflow UI에 DAG가 표시되지 않음

**원인**:
- Python 문법 에러
- 파일 권한 문제
- Scheduler가 파일을 아직 읽지 않음

**해결**:
```bash
# 1. Python 문법 검사
docker exec airflow-scheduler python /opt/airflow/dags/ml_pipeline_dag.py

# 2. 파일 권한 확인
ls -la /home/i/work/ai/lakehouse-tick/dags/

# 3. 권한 수정
chmod 644 /home/i/work/ai/lakehouse-tick/dags/*.py

# 4. Scheduler 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler

# 5. 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-scheduler | tail -50
```

---

### 문제 2: Task 실행 실패

**증상**: Task 상태가 "failed"

**해결**:
```bash
# 1. Task 로그 확인
docker exec airflow-scheduler airflow tasks logs \
  ml_pipeline_end_to_end \
  raw_to_bronze \
  2025-12-25

# 2. Worker 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-worker | grep ERROR

# 3. Task 재실행
docker exec airflow-scheduler airflow tasks clear \
  ml_pipeline_end_to_end \
  --task-regex "raw_to_bronze" \
  --start-date 2025-12-25 \
  --end-date 2025-12-25
```

---

### 문제 3: MLflow 연결 실패

**증상**: Task에서 MLflow에 로깅하지 못함

**해결**:
```bash
# 1. MLflow 상태 확인
curl http://localhost:5000/health

# 2. 네트워크 연결 테스트 (Worker에서)
docker exec airflow-worker curl http://mlflow:5000/health

# 3. 환경 변수 확인
docker exec airflow-worker env | grep MLFLOW

# 4. MLflow 재시작
docker compose -f docker-compose-mlops.yml restart mlflow
```

---

### 문제 4: 메모리 부족

**증상**: Worker 컨테이너가 재시작됨

**해결**:
```bash
# 1. 현재 메모리 사용량 확인
docker stats --no-stream

# 2. docker-compose-mlops.yml 수정
# Worker의 메모리 제한 증가:
#   deploy.resources.limits.memory: 4G  # 2G → 4G

# 3. 재시작
docker compose -f docker-compose-mlops.yml restart airflow-worker
```

---

### 문제 5: Task가 큐에서 대기 중

**증상**: Task 상태가 "queued"에서 변하지 않음

**원인**: Worker가 실행 중이지 않음

**해결**:
```bash
# 1. Worker 상태 확인
docker compose -f docker-compose-mlops.yml ps airflow-worker

# 2. Worker 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-worker | grep "celery@"

# 3. Worker가 중지되어 있다면 시작
docker compose -f docker-compose-mlops.yml up -d airflow-worker

# 4. Celery 상태 확인
docker exec airflow-worker celery --app airflow.executors.celery_executor.app inspect ping
```

---

## 빠른 참조

### 자주 사용하는 명령어

```bash
# 스택 시작
docker compose -f docker-compose-mlops.yml up -d

# 스택 중지
docker compose -f docker-compose-mlops.yml stop

# DAG 목록
docker exec airflow-scheduler airflow dags list

# DAG 실행
docker exec airflow-scheduler airflow dags trigger <dag_id>

# DAG 실행 이력
docker exec airflow-scheduler airflow dags list-runs -d <dag_id>

# Task 로그
docker exec airflow-scheduler airflow tasks logs <dag_id> <task_id> <execution_date>

# 서비스 로그
docker compose -f docker-compose-mlops.yml logs -f <service_name>

# 리소스 모니터링
docker stats mlflow airflow-webserver airflow-scheduler airflow-worker
```

### URL 빠른 접속

| 서비스 | URL | 용도 |
|--------|-----|------|
| Airflow | http://localhost:8082 | DAG 관리 |
| MLflow | http://localhost:5000 | 실험 추적 |
| Trino | http://localhost:8080/ui | 쿼리 모니터링 |
| Superset | http://localhost:8088 | BI 대시보드 |
| Grafana | http://localhost:3000 | 시스템 모니터링 |

---

## 다음 단계

1. **[실전 예제](./MLOPS_EXAMPLES.md)**: 실제 유스케이스 기반 DAG 작성
2. **[성능 최적화](./MLOPS_OPTIMIZATION.md)**: Airflow 및 MLflow 튜닝
3. **[보안 가이드](./MLOPS_SECURITY.md)**: RBAC, SSL/TLS 설정
4. **[CI/CD 통합](./MLOPS_CICD.md)**: Jenkins/GitHub Actions 연동

---

**작성**: 2025-12-26
**버전**: 1.0
**관련 문서**:
- [END_TO_END_ML_PIPELINE_MONITORING_SOLUTIONS.md](../feature/visualization/END_TO_END_ML_PIPELINE_MONITORING_SOLUTIONS.md)
- [START_HERE.md](../../START_HERE.md)
