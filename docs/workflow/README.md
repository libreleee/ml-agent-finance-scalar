# MLOps 워크플로우 문서

이 디렉토리는 Lakehouse-Tick 프로젝트의 **MLOps 워크플로우 사용법**에 대한 문서를 포함합니다.

---

## 📚 문서 목록

### 1. [빠른 시작 가이드](./QUICK_START.md) ⭐ 추천

**5분 안에 MLOps 스택 시작하기**

- MLOps 스택 최초 실행
- UI 접속 확인
- 샘플 DAG 실행
- 결과 확인

**대상**: 처음 시작하는 사용자

---

### 2. [워크플로우 가이드](./MLOPS_WORKFLOW_GUIDE.md)

**전체 MLOps 워크플로우 상세 설명**

- 아키텍처 개요
- Airflow 사용법
- MLflow 사용법
- DAG 작성 가이드
- ML 파이프라인 예제
- 모니터링 및 디버깅
- 트러블슈팅

**대상**: MLOps 스택을 실무에서 사용하는 사용자

---

### 3. [명령어 참조](./COMMAND_REFERENCE.md)

**자주 사용하는 명령어 모음**

- Docker Compose 명령어
- Airflow CLI 명령어
- MLflow CLI 명령어
- 디버깅 명령어
- 유지보수 명령어
- 빠른 참조 치트시트

**대상**: 명령어를 빠르게 찾고 싶은 사용자

---

## 🚀 어디서 시작해야 할까요?

### 처음 사용하시나요?

1. **[빠른 시작 가이드](./QUICK_START.md)** 읽기 (5분)
2. MLOps 스택 시작하기
3. 샘플 DAG 실행해보기

### 실무에서 사용하시나요?

1. **[워크플로우 가이드](./MLOPS_WORKFLOW_GUIDE.md)** 읽기
2. DAG 작성 가이드 숙지
3. 프로젝트에 맞는 DAG 작성

### 명령어만 찾으시나요?

- **[명령어 참조](./COMMAND_REFERENCE.md)** 바로 가기

---

## 📖 전체 문서 구조

```
docs/
├── workflow/                          # MLOps 워크플로우 문서 (현재 위치)
│   ├── README.md                      # 이 파일
│   ├── QUICK_START.md                 # 빠른 시작 (5분)
│   ├── MLOPS_WORKFLOW_GUIDE.md        # 전체 워크플로우 (상세)
│   └── COMMAND_REFERENCE.md           # 명령어 참조
│
├── feature/                           # 기능 설계 문서
│   └── visualization/
│       └── END_TO_END_ML_PIPELINE_MONITORING_SOLUTIONS.md
│
└── ...
```

---

## 🎯 주요 유스케이스

### 1. MLOps 스택 시작

```bash
cd /home/i/work/ai/lakehouse-tick
docker compose -f docker-compose-mlops.yml up -d
```

**참조**: [빠른 시작 가이드 - 1단계](./QUICK_START.md#1단계-mlops-스택-시작-1분)

---

### 2. 샘플 DAG 실행

**Airflow UI**:
1. http://localhost:8082 접속 (admin/admin)
2. `ml_pipeline_end_to_end` 클릭
3. "Trigger DAG" 버튼 클릭

**CLI**:
```bash
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end
```

**참조**: [빠른 시작 가이드 - 3단계](./QUICK_START.md#3단계-샘플-dag-실행-2분)

---

### 3. 새 DAG 작성

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def my_task():
    print("Hello from Airflow!")

dag = DAG('my_dag', start_date=datetime(2025, 12, 26))

task = PythonOperator(
    task_id='my_task',
    python_callable=my_task,
    dag=dag,
)
```

**참조**: [워크플로우 가이드 - DAG 작성](./MLOPS_WORKFLOW_GUIDE.md#dag-작성-가이드)

---

### 4. MLflow에 모델 로깅

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier

mlflow.set_tracking_uri("http://mlflow:5000")
mlflow.set_experiment("my-experiment")

with mlflow.start_run():
    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    mlflow.log_param("n_estimators", 100)
    mlflow.log_metric("accuracy", 0.95)
    mlflow.sklearn.log_model(model, "model")
```

**참조**: [워크플로우 가이드 - MLflow 사용법](./MLOPS_WORKFLOW_GUIDE.md#mlflow-사용법)

---

### 5. 트러블슈팅

#### DAG가 표시되지 않아요

```bash
# 파일 권한 확인
ls -la /home/i/work/ai/lakehouse-tick/dags/

# Scheduler 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-scheduler | tail -50

# Scheduler 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler
```

**참조**: [워크플로우 가이드 - 트러블슈팅](./MLOPS_WORKFLOW_GUIDE.md#트러블슈팅)

---

## 🔗 관련 문서

### 프로젝트 문서

- [START_HERE.md](../../START_HERE.md) - 프로젝트 시작 가이드
- [GETTING_STARTED.md](../../GETTING_STARTED.md) - 전체 시스템 시작 가이드

### MLOps 설계 문서

- [END_TO_END_ML_PIPELINE_MONITORING_SOLUTIONS.md](../feature/visualization/END_TO_END_ML_PIPELINE_MONITORING_SOLUTIONS.md)
  - 6가지 ML 솔루션 비교
  - Airflow + MLflow 선택 이유
  - 옵션 2: 별도 docker-compose-mlops.yml 구현 가이드

### 설정 파일

- [docker-compose-mlops.yml](../../docker-compose-mlops.yml) - MLOps 스택 정의
- [.env](../../.env) - 환경 변수
- [dags/](../../dags/) - Airflow DAG 파일

---

## 💡 자주 묻는 질문

### Q1. Airflow와 MLflow의 차이점은?

**Airflow**: 워크플로우 오케스트레이션 도구
- DAG(방향성 비순환 그래프) 기반 작업 스케줄링
- Task 의존성 관리
- 실행 이력 추적

**MLflow**: ML 실험 추적 및 모델 레지스트리
- 실험 파라미터/메트릭 로깅
- 모델 버전 관리
- 모델 배포

**함께 사용**: Airflow로 ML 파이프라인을 실행하고, MLflow로 실험 결과를 추적

---

### Q2. 기존 Lakehouse 인프라와의 관계는?

```
┌─────────────────────────────────────┐
│   Lakehouse 인프라 (docker-compose.yml)│
│   - Trino, Iceberg, SeaweedFS      │
└──────────────┬──────────────────────┘
               │ (lakehouse-net)
               ▼
┌─────────────────────────────────────┐
│   MLOps 스택 (docker-compose-mlops.yml) │
│   - Airflow, MLflow                │
└─────────────────────────────────────┘
```

**독립 실행**: 각각 별도로 시작/중지 가능
**네트워크 공유**: `lakehouse-net`으로 서비스 간 통신

---

### Q3. 포트가 충돌하면 어떻게 하나요?

**현재 사용 중인 포트**:
- Airflow: 8082
- MLflow: 5000
- Redis: 6379

**포트 변경 방법**:
1. [docker-compose-mlops.yml](../../docker-compose-mlops.yml) 열기
2. `ports` 섹션 수정
   ```yaml
   ports:
     - "NEW_PORT:8080"  # 예: "8090:8080"
   ```
3. 스택 재시작
   ```bash
   docker compose -f docker-compose-mlops.yml restart
   ```

---

### Q4. 데이터는 어디에 저장되나요?

**Airflow 메타데이터**: PostgreSQL 볼륨 (`airflow-postgres-data`)
**MLflow 메타데이터**: SQLite 파일 (`mlflow-data` 볼륨)
**MLflow 아티팩트**: SeaweedFS S3 (`s3://lakehouse/mlflow/`)
**DAG 파일**: 호스트 디렉토리 (`./dags/`)
**로그**: 호스트 디렉토리 (`./logs/`)

---

### Q5. 운영 환경에서 사용해도 되나요?

**현재 구성**: 개발/테스트 환경용

**운영 환경 전환 시 변경 사항**:
1. **보안 강화**
   - 기본 비밀번호 변경
   - RBAC 활성화
   - SSL/TLS 적용

2. **성능 최적화**
   - MLflow: SQLite → PostgreSQL
   - Worker 스케일아웃
   - 리소스 제약 조정

3. **고가용성**
   - Redis Sentinel/Cluster
   - PostgreSQL Replication
   - 백업 자동화

---

## 📝 피드백

문서 개선 제안이나 오류 발견 시:
- GitHub Issue 생성
- Pull Request 제출

---

**작성**: 2025-12-26
**버전**: 1.0
**최종 업데이트**: 2025-12-26
