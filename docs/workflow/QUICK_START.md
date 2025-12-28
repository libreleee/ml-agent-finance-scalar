# MLOps 빠른 시작 가이드

## 🚀 5분 안에 시작하기

이 가이드는 MLOps 스택을 **최소한의 단계**로 시작할 수 있도록 도와줍니다.

---

## 전제 조건

- Docker 및 Docker Compose 설치됨
- 기존 Lakehouse 인프라 실행 중 (`docker compose ps`로 확인)

---

## 1단계: MLOps 스택 시작 (1분)

```bash
cd /home/i/work/ai/lakehouse-tick

# MLOps 스택 시작
docker compose -f docker-compose-mlops.yml up -d

# 상태 확인 (모든 서비스가 "Up (healthy)" 상태가 될 때까지 대기)
docker compose -f docker-compose-mlops.yml ps
```

**예상 출력**:
```
NAME                    STATUS
airflow-postgres        Up (healthy)
airflow-redis           Up (healthy)
airflow-scheduler       Up (healthy)
airflow-webserver       Up (healthy)
airflow-worker          Up (healthy)
mlflow                  Up (healthy)
```

---

## 2단계: UI 접속 확인 (30초)

### Airflow UI

1. 브라우저 열기
2. http://localhost:8082 접속
3. 로그인: `admin` / `admin`
4. DAGs 페이지에서 `ml_pipeline_end_to_end` 확인

### MLflow UI

1. 브라우저 새 탭 열기
2. http://localhost:5000 접속
3. Experiments 목록 확인

---

## 3단계: 샘플 DAG 실행 (2분)

### 📊 DAG 구조 (7단계 ML 파이프라인)

Airflow UI의 Graph View에서 다음과 같은 흐름을 확인할 수 있습니다:

```
┌──────────────────┐
│ raw_to_bronze    │ 📥 원시 데이터 수집
└────────┬─────────┘
         ↓
┌──────────────────┐
│bronze_to_silver  │ 🧹 데이터 정제
└────────┬─────────┘
         ↓
┌──────────────────┐
│ silver_to_gold   │ 💎 비즈니스 로직 적용
└────────┬─────────┘
         ↓
┌──────────────────┐
│feature_engineering│ 🔧 ML 피처 생성
└────────┬─────────┘
         ↓
┌──────────────────┐
│ model_training   │ 🧠 모델 학습
└────────┬─────────┘
         ↓
┌──────────────────┐
│model_evaluation  │ 📊 모델 평가
└────────┬─────────┘
         ↓
┌──────────────────┐
│ model_registry   │ 📦 모델 등록 (MLflow)
└──────────────────┘
```

**Task 색상 의미**:
- 🟢 **녹색**: 성공
- 🟡 **노란색**: 실행 중
- 🔴 **빨간색**: 실패
- ⚪ **회색**: 대기 중

---

### Airflow UI에서 실행

1. http://localhost:8082 접속
2. `ml_pipeline_end_to_end` DAG 클릭
3. 우측 상단 "Trigger DAG" 버튼 클릭
4. **Graph View** 탭에서 위 다이어그램 형태의 실행 상태 확인

### CLI에서 실행

```bash
# DAG 활성화
docker exec airflow-scheduler airflow dags unpause ml_pipeline_end_to_end

# DAG 실행
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# 실행 상태 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end
```

---

## 4단계: MLflow에서 결과 확인 (1분)

1. http://localhost:5000 접속
2. "lakehouse_ml_pipeline" 실험 클릭
3. 최근 Run 클릭
4. Parameters 및 Metrics 확인

**확인할 항목**:
- Parameters: `layer`, `transformation` 등
- Metrics: `rows_ingested`, `quality_score`, `accuracy`, `f1_score` 등

---

## 완료! 🎉

이제 MLOps 스택이 정상 작동합니다.

### 다음 단계

#### 실시간 모니터링

```bash
# 실시간 로그 확인
docker compose -f docker-compose-mlops.yml logs -f

# Worker 로그만 확인
docker compose -f docker-compose-mlops.yml logs -f airflow-worker

# 리소스 사용률 확인
docker stats mlflow airflow-webserver airflow-scheduler airflow-worker
```

#### 새 DAG 추가

1. `dags/` 디렉토리에 Python 파일 생성
2. 30초 대기 (Airflow가 자동으로 감지)
3. Airflow UI에서 확인

#### 학습 더하기

- **상세 가이드**: [MLOPS_WORKFLOW_GUIDE.md](./MLOPS_WORKFLOW_GUIDE.md)
- **DAG 작성법**: [MLOPS_WORKFLOW_GUIDE.md#dag-작성-가이드](./MLOPS_WORKFLOW_GUIDE.md#dag-작성-가이드)
- **트러블슈팅**: [MLOPS_WORKFLOW_GUIDE.md#트러블슈팅](./MLOPS_WORKFLOW_GUIDE.md#트러블슈팅)

---

## 자주 묻는 질문

### Q1. Airflow UI가 로딩되지 않아요

```bash
# Webserver 상태 확인
docker compose -f docker-compose-mlops.yml ps airflow-webserver

# 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-webserver | tail -50

# 재시작
docker compose -f docker-compose-mlops.yml restart airflow-webserver
```

### Q2. DAG가 표시되지 않아요

```bash
# DAG 파일 권한 확인
ls -la /home/i/work/ai/lakehouse-tick/dags/

# Scheduler 로그 확인
docker compose -f docker-compose-mlops.yml logs airflow-scheduler | grep ml_pipeline

# 파일 권한 수정
chmod 644 /home/i/work/ai/lakehouse-tick/dags/*.py
```

### Q3. Task가 실행되지 않아요

```bash
# Worker 상태 확인
docker compose -f docker-compose-mlops.yml ps airflow-worker

# Worker가 없다면 시작
docker compose -f docker-compose-mlops.yml up -d airflow-worker

# Celery 연결 확인
docker exec airflow-worker celery --app airflow.executors.celery_executor.app inspect ping
```

### Q4. MLflow에 로그가 기록되지 않아요

```bash
# MLflow 상태 확인
curl http://localhost:5000/health

# 네트워크 연결 테스트
docker exec airflow-worker curl http://mlflow:5000/health

# MLflow 재시작
docker compose -f docker-compose-mlops.yml restart mlflow
```

---

## 스택 중지

```bash
# 중지 (데이터 유지)
docker compose -f docker-compose-mlops.yml stop

# 완전 제거 (데이터 유지)
docker compose -f docker-compose-mlops.yml down

# 완전 제거 (데이터 삭제)
docker compose -f docker-compose-mlops.yml down -v
```

---

**작성**: 2025-12-26
**버전**: 1.0
**다음**: [MLOPS_WORKFLOW_GUIDE.md](./MLOPS_WORKFLOW_GUIDE.md) - 상세 사용법

---

## 📖 처음부터 실행하는 전체 가이드

처음 시작하는 경우 아래 순서대로 따라하세요.

### 🔧 실행 환경

- **Python 버전**: Python 3.11
- **Airflow 이미지**: `apache/airflow:2.8.0-python3.11`
- **MLflow 버전**: 2.9.2

---

### 📋 전체 실행 순서

#### 1️⃣ Lakehouse 인프라 시작

```bash
cd /home/i/work/ai/lakehouse-tick

# Lakehouse 인프라 시작 (Trino, SeaweedFS, Hive 등)
docker compose up -d

# 상태 확인
docker compose ps
```

#### 2️⃣ MLOps 스택 시작 (Airflow + MLflow)

```bash
# MLOps 스택 시작
docker compose -f docker-compose-mlops.yml up -d

# 상태 확인
docker compose -f docker-compose-mlops.yml ps
```

**예상 출력**:
```
NAME                    STATUS
airflow-postgres        Up (healthy)
airflow-redis           Up (healthy)
airflow-scheduler       Up (healthy)
airflow-webserver       Up (healthy)
airflow-worker          Up (healthy)
mlflow                  Up (healthy)
```

#### 3️⃣ Airflow 초기화 (최초 1회만 필요)

```bash
# Airflow DB 초기화
docker compose -f docker-compose-mlops.yml exec airflow-webserver airflow db migrate

# Admin 사용자 생성
docker compose -f docker-compose-mlops.yml exec airflow-webserver \
  airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

#### 4️⃣ 접속 확인

```bash
# Airflow UI 접속
echo "Airflow UI: http://localhost:8082"
echo "Login: admin / admin"

# MLflow UI 접속
echo "MLflow UI: http://localhost:5000"
```

---

### ▶️ DAG 실행 방법

#### 방법 1: CLI로 실행 (추천)

```bash
# DAG 목록 확인
docker exec airflow-scheduler airflow dags list

# DAG 실행
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# 실행 상태 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end --state running

# 완료된 실행 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end
```

#### 방법 2: Airflow UI에서 실행

1. 브라우저에서 **http://localhost:8082** 접속
2. Login: `admin` / `admin`
3. `ml_pipeline_end_to_end` DAG 클릭
4. 우측 상단 **"Trigger DAG"** 버튼 클릭
5. **Graph View** 탭에서 7단계 파이프라인 시각화 확인

---

### 📊 결과 확인 방법

#### 옵션 1: Airflow UI에서 확인

1. **http://localhost:8082** 접속
2. `ml_pipeline_end_to_end` DAG 클릭
3. **Graph View** 탭 → 7단계 파이프라인 시각화
4. 각 Task 클릭 → **Logs** 탭에서 실행 로그 확인

**Task 색상 의미**:
- 🟢 **녹색**: 성공
- 🟡 **노란색**: 실행 중
- 🔴 **빨간색**: 실패
- ⚪ **회색**: 대기 중

#### 옵션 2: CLI로 로그 확인

```bash
# Worker 로그 실시간 확인
docker compose -f docker-compose-mlops.yml logs -f airflow-worker

# Scheduler 로그 확인
docker compose -f docker-compose-mlops.yml logs -f airflow-scheduler

# 특정 Task 로그 확인
docker exec airflow-scheduler airflow tasks logs \
  ml_pipeline_end_to_end \
  raw_to_bronze \
  2025-12-26
```

#### 옵션 3: MLflow UI에서 실험 결과 확인

1. **http://localhost:5000** 접속
2. **Experiments** 목록에서 `lakehouse_ml_pipeline` 클릭
3. 최근 Run 클릭
4. **Parameters** 및 **Metrics** 확인

**확인 가능한 메트릭**:
- Parameters: `layer`, `transformation`, `model_type` 등
- Metrics: `rows_ingested`, `quality_score`, `accuracy`, `f1_score` 등

---

### 🎯 요약 체크리스트

#### ✅ 서비스 실행 확인
```bash
# 전체 서비스 상태
docker compose ps
docker compose -f docker-compose-mlops.yml ps

# 개별 서비스 헬스 확인
curl -f http://localhost:8082/health  # Airflow
curl -f http://localhost:5000/health  # MLflow
```

#### ✅ DAG 실행 확인
```bash
# DAG 목록
docker exec airflow-scheduler airflow dags list

# DAG 실행
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# 실행 상태
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end
```

#### ✅ 접속 URL
- **Airflow UI**: http://localhost:8082 (admin/admin)
- **MLflow UI**: http://localhost:5000
- **Trino UI**: http://localhost:8080
- **Grafana**: http://localhost:3000 (admin/admin)
- **Superset**: http://localhost:8088 (admin/admin)

---

### 🔄 일상적인 사용

#### DAG 매일 실행하기

```bash
# 1. DAG 활성화 (자동 스케줄링)
docker exec airflow-scheduler airflow dags unpause ml_pipeline_end_to_end

# 2. 수동 실행 (즉시 실행)
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# 3. 실행 이력 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end
```

#### 로그 모니터링

```bash
# 실시간 로그
docker compose -f docker-compose-mlops.yml logs -f

# 특정 서비스만
docker compose -f docker-compose-mlops.yml logs -f airflow-worker

# 최근 100줄
docker compose -f docker-compose-mlops.yml logs --tail=100 airflow-scheduler
```

#### 리소스 모니터링

```bash
# CPU/메모리 사용률
docker stats mlflow airflow-webserver airflow-scheduler airflow-worker

# 디스크 사용량
docker system df -v | grep -E 'mlflow|airflow'
```

---

### 🛑 스택 중지 및 재시작

#### 중지 (데이터 유지)

```bash
# MLOps 스택만 중지
docker compose -f docker-compose-mlops.yml stop

# Lakehouse 인프라는 계속 실행 상태 유지
docker compose ps
```

#### 재시작

```bash
# MLOps 스택 재시작
docker compose -f docker-compose-mlops.yml restart

# 특정 서비스만 재시작
docker compose -f docker-compose-mlops.yml restart airflow-worker
```

#### 완전 제거

```bash
# 컨테이너 제거 (볼륨 유지)
docker compose -f docker-compose-mlops.yml down

# 컨테이너 + 볼륨 모두 제거 (주의: 데이터 삭제)
docker compose -f docker-compose-mlops.yml down -v
```

---

### 💡 추가 팁

#### uv 가상환경 패키지 관리

```bash
# 가상환경 활성화
cd /home/i/work/ai/lakehouse-tick
. ../.venv/bin/activate

# 패키지 설치
uv pip install <package-name>

# 패키지 목록 확인
uv pip list

# requirements.txt 생성
uv pip freeze > requirements.txt
```

#### DAG 파일 수정 후 적용

```bash
# 1. dags/ 디렉토리에서 Python 파일 수정
vim /home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py

# 2. 30초 대기 (Airflow가 자동 감지)

# 3. Scheduler 로그에서 인식 확인
docker compose -f docker-compose-mlops.yml logs airflow-scheduler | tail -20

# 4. (선택) Scheduler 재시작으로 즉시 적용
docker compose -f docker-compose-mlops.yml restart airflow-scheduler
```

---

## 🔗 Docker Bind Mount: 소스 코드 연결 원리

### 📁 프로젝트 파일이 Docker 컨테이너에 연결되는 방식

#### 1️⃣ Bind Mount 구조

`docker-compose-mlops.yml`에서 설정된 볼륨 마운트:

```yaml
volumes:
  - ./dags:/opt/airflow/dags           # 호스트 경로:컨테이너 경로
  - ./logs/airflow:/opt/airflow/logs
  - ./plugins:/opt/airflow/plugins
```

**경로 매핑**:
```
호스트 (실제 컴퓨터)                          컨테이너 (Docker 내부)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/home/i/work/ai/lakehouse-tick/dags    →    /opt/airflow/dags
                                             (실시간 동기화)
```

---

#### 2️⃣ 실시간 동기화

호스트에서 파일을 수정하면:

```bash
# 호스트에서 편집
vim /home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py
```

**즉시** 컨테이너 내부에서도 동일한 변경사항이 반영됩니다:

```bash
# 컨테이너 내부에서 확인 (변경사항이 그대로 보임)
docker exec airflow-scheduler cat /opt/airflow/dags/ml_pipeline_dag.py
```

---

#### 3️⃣ 연결 확인 방법

##### 호스트에서 파일 확인
```bash
ls -la /home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py
```

##### 컨테이너에서 파일 확인
```bash
docker exec airflow-scheduler ls -la /opt/airflow/dags/ml_pipeline_dag.py
```

##### Airflow가 DAG 인식했는지 확인
```bash
docker exec airflow-scheduler airflow dags list | grep ml_pipeline
```

**예상 출력**:
```
ml_pipeline_end_to_end | ml_pipeline_dag.py | airflow | False
```

---

#### 4️⃣ 왜 이 방식을 사용하는가?

**장점**:
- ✅ **컨테이너 재빌드 불필요**: DAG 파일 수정 후 `docker compose up -d` 다시 실행 안 해도 됨
- ✅ **개발 편의성**: 로컬 IDE(VSCode, PyCharm 등)에서 편집 → 즉시 Airflow가 인식
- ✅ **로그 접근성**: 컨테이너 내부 로그가 호스트 `./logs/airflow/`에 실시간 저장
- ✅ **백업 용이**: 호스트 디렉토리만 백업하면 모든 DAG 파일 보존

**단점**:
- ⚠️ **파일 권한 문제**: Airflow 컨테이너는 UID 50000으로 실행되므로 권한 조정 필요
- ⚠️ **성능 영향**: Windows/macOS에서는 I/O 성능이 느릴 수 있음 (Linux는 네이티브 속도)

---

#### 5️⃣ Airflow Scheduler의 파일 감지 메커니즘

Airflow Scheduler는 `/opt/airflow/dags/` 디렉토리를 **30초마다 스캔**합니다:

```
[1] Scheduler가 /opt/airflow/dags/ 스캔
    └─ 새 .py 파일 발견 → DAG 로드
    └─ 기존 파일 수정 → DAG 리로드
    └─ 파일 삭제 → DAG 목록에서 제거

[2] 호스트에서 ml_pipeline_dag.py 수정
    └─ Bind Mount로 즉시 컨테이너에 반영

[3] 최대 30초 후 Scheduler가 변경사항 감지
    └─ Airflow UI에 새 DAG 표시
```

---

#### 6️⃣ 전체 데이터 흐름

```
[1] 개발자가 로컬에서 DAG 작성
    └─ 📄 /home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py

[2] Docker Bind Mount가 자동 동기화
    └─ 🔗 호스트 ./dags ←→ 컨테이너 /opt/airflow/dags

[3] Airflow Scheduler가 파일 감지 (30초 주기)
    └─ 🔍 /opt/airflow/dags/ml_pipeline_dag.py 읽기

[4] DAG 파싱 및 메타데이터 DB 저장
    └─ 💾 PostgreSQL (airflow-postgres 컨테이너)

[5] Airflow UI에서 DAG 표시
    └─ 🌐 http://localhost:8082

[6] DAG 실행 시 Worker가 실제 코드 실행
    └─ ⚙️  Celery Worker (airflow-worker 컨테이너)
```

---

#### 7️⃣ 트러블슈팅: DAG 파일이 인식되지 않을 때

##### 문제 1: 파일 권한 오류
```bash
# 증상: Airflow UI에 DAG가 표시되지 않음

# 해결 1: 파일 권한 확인
ls -l /home/i/work/ai/lakehouse-tick/dags/

# 해결 2: 권한 수정 (Airflow는 UID 50000 사용)
sudo chown -R 50000:50000 /home/i/work/ai/lakehouse-tick/dags/
```

##### 문제 2: Python 문법 에러
```bash
# 증상: Scheduler 로그에 에러 메시지

# 해결: 컨테이너 내부에서 Python 문법 검사
docker exec airflow-scheduler python /opt/airflow/dags/ml_pipeline_dag.py
```

##### 문제 3: Bind Mount가 작동하지 않음
```bash
# 증상: 호스트에서 파일 수정했는데 컨테이너에 반영 안 됨

# 해결 1: 볼륨 마운트 확인
docker inspect airflow-scheduler | grep -A 10 Mounts

# 해결 2: 컨테이너 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler
```

---

#### 8️⃣ 실전 예제: DAG 파일 수정부터 실행까지

```bash
# Step 1: 호스트에서 DAG 파일 수정
cd /home/i/work/ai/lakehouse-tick
vim dags/ml_pipeline_dag.py
# (파일 내용 수정 후 저장)

# Step 2: 파일이 컨테이너에 반영되었는지 확인
docker exec airflow-scheduler cat /opt/airflow/dags/ml_pipeline_dag.py | head -20

# Step 3: 30초 대기 또는 즉시 적용
docker compose -f docker-compose-mlops.yml restart airflow-scheduler

# Step 4: Airflow가 DAG를 인식했는지 확인
docker exec airflow-scheduler airflow dags list | grep ml_pipeline

# Step 5: DAG 실행
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# Step 6: 실행 상태 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end
```

---

**정리**: 이 방식 덕분에 **소스 코드는 프로젝트 파일에 있지만, Docker 컨테이너에서 실행 가능**합니다! 🎯

---

아니요! Scheduler는 파일을 직접 실행하지 않습니다. 정확한 역할 분담을 설명하겠습니다:
🔄 Scheduler vs Worker: 역할 분담
📋 Airflow Scheduler의 역할
Scheduler는 "관리자"입니다 - 실행은 안 하고 지시만 합니다:

[Scheduler가 하는 일]
1. DAG 파일 스캔 (30초마다)
   └─ /opt/airflow/dags/*.py 읽기
   
2. DAG 파싱 (파이썬 코드 분석)
   └─ Task 목록 추출
   └─ Task 의존성 파악 (A >> B >> C)
   └─ 스케줄 정보 확인 (매일 02:00)
   
3. Task 실행 시점 판단
   └─ "지금 실행해야 할 Task가 있나?"
   └─ "의존성이 충족되었나?"
   
4. Task를 Queue에 전송
   └─ Redis (Celery Broker)에 Task 전달
   └─ "누군가 이 Task 실행해줘!"
⚙️ Airflow Worker의 역할
Worker는 "실행자"입니다 - 실제 코드를 실행합니다:

[Worker가 하는 일]
1. Redis Queue를 모니터링
   └─ "실행할 Task 있나?"
   
2. Task를 Queue에서 가져오기
   └─ "raw_to_bronze Task 받았다!"
   
3. 실제 Python 함수 실행
   └─ ml_pipeline_dag.py의 raw_to_bronze() 함수 호출
   └─ MLflow 코드 실행
   └─ 데이터 처리 로직 수행
   
4. 결과를 PostgreSQL에 저장
   └─ "성공했어!" 또는 "실패했어!"
🎬 실제 실행 흐름 예시
시나리오: ml_pipeline_end_to_end DAG 실행

[1] Scheduler가 DAG 파일 스캔
    📄 /opt/airflow/dags/ml_pipeline_dag.py
    └─ "오, ml_pipeline_end_to_end DAG 발견!"
    └─ "7개 Task가 있네: raw_to_bronze, bronze_to_silver, ..."
    └─ "의존성: raw_to_bronze >> bronze_to_silver >> ..."

[2] Scheduler가 실행 시점 판단
    ⏰ schedule=timedelta(days=1)
    └─ "매일 실행해야 하는데..."
    └─ "지금 2025-12-26 00:00:00이네"
    └─ "실행 시점이다!"

[3] Scheduler가 첫 번째 Task를 Queue에 전송
    📤 Redis Queue에 전송
    └─ Task: "raw_to_bronze"
    └─ DAG: "ml_pipeline_end_to_end"
    └─ 실행 날짜: 2025-12-26
    └─ "누군가 이거 실행해!"

[4] Worker가 Queue를 체크
    📥 Redis에서 Task 수신
    └─ "raw_to_bronze Task 받았다!"
    └─ "실행 시작!"

[5] Worker가 실제 코드 실행 ⭐ 여기서 실행됨!
    🐍 Python 함수 호출
    └─ def raw_to_bronze(**context):
    └─     import mlflow
    └─     mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    └─     with mlflow.start_run(run_name="raw_to_bronze"):
    └─         mlflow.log_param("layer", "bronze")
    └─         mlflow.log_metric("rows_ingested", 10000)
    └─         print("✅ Bronze 레이어에 10000개 행 수집 완료")
    └─         return {"rows_ingested": 10000}

[6] Worker가 결과를 PostgreSQL에 저장
    💾 Airflow DB 업데이트
    └─ task_instance 테이블
    └─ state: "success"
    └─ end_date: 2025-12-26 00:01:30

[7] Scheduler가 다음 Task 판단
    📋 의존성 체크
    └─ "raw_to_bronze가 성공했네"
    └─ "다음은 bronze_to_silver야"
    └─ "Queue에 전송!"

[8] Worker가 두 번째 Task 실행
    🐍 bronze_to_silver() 함수 실행
    └─ (5번 과정 반복)

... (7개 Task 모두 완료될 때까지 반복)


docker logs airflow-scheduler 2>&1 | grep -A 5 "ml_pipeline_end_to_end" | tail -20

✅ Bind Mount 구조 - Volume mount configuration explanation
✅ 실시간 동기화 - Real-time synchronization details
✅ 연결 확인 방법 - Commands to verify the connection
✅ 왜 이 방식을 사용하는가 - Advantages explanation
✅ Scheduler 파일 감지 메커니즘 - 30-second scan cycle details
✅ 전체 데이터 흐름 - 6-step data flow diagram
✅ 트러블슈팅 - Troubleshooting guide for common issues
✅ 실전 예제 - Practical step-by-step example
The last work completed was explaining the Schedulerㄹ