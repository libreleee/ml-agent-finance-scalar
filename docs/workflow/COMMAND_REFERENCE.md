# MLOps 명령어 참조

## 📚 목차

1. [Docker Compose 명령어](#docker-compose-명령어)
2. [Airflow CLI 명령어](#airflow-cli-명령어)
3. [MLflow CLI 명령어](#mlflow-cli-명령어)
4. [디버깅 명령어](#디버깅-명령어)
5. [유지보수 명령어](#유지보수-명령어)

---

## Docker Compose 명령어

### 스택 관리

```bash
# MLOps 스택 시작
docker compose -f docker-compose-mlops.yml up -d

# 특정 서비스만 시작
docker compose -f docker-compose-mlops.yml up -d mlflow

# 스택 중지 (데이터 유지)
docker compose -f docker-compose-mlops.yml stop

# 스택 완전 제거 (데이터 유지)
docker compose -f docker-compose-mlops.yml down

# 스택 완전 제거 (데이터 삭제)
docker compose -f docker-compose-mlops.yml down -v

# 스택 재시작
docker compose -f docker-compose-mlops.yml restart

# 특정 서비스만 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler
```

### 상태 확인

```bash
# 전체 서비스 상태
docker compose -f docker-compose-mlops.yml ps

# 특정 서비스 상태
docker compose -f docker-compose-mlops.yml ps mlflow

# 리소스 사용률
docker compose -f docker-compose-mlops.yml top
```

### 로그

```bash
# 전체 로그 (실시간)
docker compose -f docker-compose-mlops.yml logs -f

# 특정 서비스 로그
docker compose -f docker-compose-mlops.yml logs -f airflow-scheduler

# 최근 N줄만 보기
docker compose -f docker-compose-mlops.yml logs --tail=100 airflow-worker

# 특정 시간 이후 로그
docker compose -f docker-compose-mlops.yml logs --since="2025-12-26T00:00:00"

# 여러 서비스 로그 동시에
docker compose -f docker-compose-mlops.yml logs -f airflow-scheduler airflow-worker
```

---

## Airflow CLI 명령어

### DAG 관리

```bash
# DAG 목록
docker exec airflow-scheduler airflow dags list

# DAG 상세 정보
docker exec airflow-scheduler airflow dags show ml_pipeline_end_to_end

# DAG 활성화
docker exec airflow-scheduler airflow dags unpause ml_pipeline_end_to_end

# DAG 비활성화
docker exec airflow-scheduler airflow dags pause ml_pipeline_end_to_end

# DAG 트리거 (수동 실행)
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# DAG 실행 이력
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end

# 실행 중인 DAG만 보기
docker exec airflow-scheduler airflow dags list-runs --state running

# 실패한 DAG만 보기
docker exec airflow-scheduler airflow dags list-runs --state failed

# 특정 기간의 DAG 실행
docker exec airflow-scheduler airflow dags list-runs \
  -d ml_pipeline_end_to_end \
  --start-date 2025-12-25 \
  --end-date 2025-12-26
```

### Task 관리

```bash
# Task 목록
docker exec airflow-scheduler airflow tasks list ml_pipeline_end_to_end

# Task 상태 확인
docker exec airflow-scheduler airflow tasks states-for-dag-run \
  ml_pipeline_end_to_end \
  manual__2025-12-25T15:12:37+00:00

# Task 로그 보기
docker exec airflow-scheduler airflow tasks logs \
  ml_pipeline_end_to_end \
  raw_to_bronze \
  2025-12-25

# Task 테스트 (실제 실행 없이 테스트)
docker exec airflow-scheduler airflow tasks test \
  ml_pipeline_end_to_end \
  raw_to_bronze \
  2025-12-25

# Task 재실행 (Clear)
docker exec airflow-scheduler airflow tasks clear \
  ml_pipeline_end_to_end \
  --task-regex "raw_to_bronze" \
  --start-date 2025-12-25 \
  --end-date 2025-12-25

# 실패한 Task만 재실행
docker exec airflow-scheduler airflow tasks clear \
  ml_pipeline_end_to_end \
  --only-failed \
  --start-date 2025-12-25

# 다운스트림 Task까지 재실행
docker exec airflow-scheduler airflow tasks clear \
  ml_pipeline_end_to_end \
  --task-regex "raw_to_bronze" \
  --downstream \
  --start-date 2025-12-25
```

### 사용자 관리

```bash
# 사용자 목록
docker exec airflow-webserver airflow users list

# 사용자 생성
docker exec airflow-webserver airflow users create \
  --username analyst \
  --firstname Data \
  --lastname Analyst \
  --role Viewer \
  --email analyst@example.com \
  --password analyst123

# 사용자 삭제
docker exec airflow-webserver airflow users delete --username analyst

# 비밀번호 변경
docker exec airflow-webserver airflow users reset-password \
  --username admin \
  --password newpassword
```

### 연결 관리

```bash
# 연결 목록
docker exec airflow-scheduler airflow connections list

# 연결 추가 (Trino)
docker exec airflow-scheduler airflow connections add \
  --conn-id trino_default \
  --conn-type trino \
  --conn-host trino \
  --conn-port 8080 \
  --conn-login user

# 연결 삭제
docker exec airflow-scheduler airflow connections delete --conn-id trino_default

# 연결 테스트
docker exec airflow-scheduler airflow connections test trino_default
```

### 변수 관리

```bash
# 변수 목록
docker exec airflow-scheduler airflow variables list

# 변수 설정
docker exec airflow-scheduler airflow variables set \
  my_variable "my_value"

# 변수 가져오기
docker exec airflow-scheduler airflow variables get my_variable

# 변수 삭제
docker exec airflow-scheduler airflow variables delete my_variable

# JSON 파일에서 변수 Import
docker exec airflow-scheduler airflow variables import /path/to/variables.json
```

### 데이터베이스 관리

```bash
# DB 초기화
docker exec airflow-webserver airflow db init

# DB 마이그레이션
docker exec airflow-webserver airflow db migrate

# DB 리셋 (주의: 모든 데이터 삭제)
docker exec airflow-webserver airflow db reset

# DB 상태 확인
docker exec airflow-webserver airflow db check
```

---

## MLflow CLI 명령어

### 실험 관리 (REST API)

```bash
# 실험 목록
curl -s "http://localhost:5000/api/2.0/mlflow/experiments/search?max_results=100"

# 실험 생성
curl -X POST "http://localhost:5000/api/2.0/mlflow/experiments/create" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-experiment"}'

# 실험 삭제
curl -X POST "http://localhost:5000/api/2.0/mlflow/experiments/delete" \
  -H "Content-Type: application/json" \
  -d '{"experiment_id": "1"}'
```

### Run 관리

```bash
# Run 검색
curl -s "http://localhost:5000/api/2.0/mlflow/runs/search?max_results=100"

# 특정 실험의 Run 검색
curl -s "http://localhost:5000/api/2.0/mlflow/runs/search" \
  -H "Content-Type: application/json" \
  -d '{
    "experiment_ids": ["1"],
    "max_results": 100
  }'

# Run 삭제
curl -X POST "http://localhost:5000/api/2.0/mlflow/runs/delete" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "abc123"}'
```

### 모델 레지스트리

```bash
# 등록된 모델 목록
curl -s "http://localhost:5000/api/2.0/mlflow/registered-models/search"

# 모델 버전 목록
curl -s "http://localhost:5000/api/2.0/mlflow/model-versions/search" \
  -H "Content-Type: application/json" \
  -d '{"filter": "name=\"my-model\""}'

# 모델 버전 Stage 변경
curl -X POST "http://localhost:5000/api/2.0/mlflow/model-versions/transition-stage" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-model",
    "version": "1",
    "stage": "Production"
  }'
```

---

## 디버깅 명령어

### 컨테이너 내부 접속

```bash
# Airflow Scheduler 컨테이너 접속
docker exec -it airflow-scheduler bash

# Airflow Worker 컨테이너 접속
docker exec -it airflow-worker bash

# MLflow 컨테이너 접속
docker exec -it mlflow sh

# PostgreSQL 컨테이너 접속
docker exec -it airflow-postgres psql -U airflow -d airflow
```

### 네트워크 디버깅

```bash
# MLflow 연결 테스트 (Worker에서)
docker exec airflow-worker curl http://mlflow:5000/health

# Trino 연결 테스트
docker exec airflow-worker curl http://trino:8080/v1/info

# SeaweedFS S3 연결 테스트
docker exec mlflow curl http://seaweedfs-s3:8333

# DNS 확인
docker exec airflow-worker nslookup mlflow
```

### 파일 시스템 확인

```bash
# DAG 디렉토리 확인
docker exec airflow-scheduler ls -la /opt/airflow/dags/

# 로그 디렉토리 확인
docker exec airflow-scheduler ls -la /opt/airflow/logs/

# MLflow 데이터 디렉토리 확인
docker exec mlflow ls -la /mlflow/
```

### Python 환경 확인

```bash
# 설치된 패키지 확인
docker exec airflow-worker pip list

# MLflow 버전 확인
docker exec airflow-worker python -c "import mlflow; print(mlflow.__version__)"

# Scikit-learn 버전 확인
docker exec airflow-worker python -c "import sklearn; print(sklearn.__version__)"
```

---

## 유지보수 명령어

### 백업

```bash
# Airflow DB 백업
docker exec airflow-postgres pg_dump -U airflow airflow > airflow-backup-$(date +%Y%m%d).sql

# MLflow 데이터 백업
docker exec mlflow tar -czf - /mlflow > mlflow-backup-$(date +%Y%m%d).tar.gz

# DAG 파일 백업
tar -czf dags-backup-$(date +%Y%m%d).tar.gz /home/i/work/ai/lakehouse-tick/dags/

# 전체 백업 스크립트
cat > backup-mlops.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/mlops-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

docker exec airflow-postgres pg_dump -U airflow airflow > $BACKUP_DIR/airflow-db.sql
docker exec mlflow tar -czf - /mlflow > $BACKUP_DIR/mlflow-data.tar.gz
tar -czf $BACKUP_DIR/dags.tar.gz /home/i/work/ai/lakehouse-tick/dags/

echo "✅ Backup completed: $BACKUP_DIR"
EOF

chmod +x backup-mlops.sh
./backup-mlops.sh
```

### 복원

```bash
# Airflow DB 복원
cat airflow-backup-20251226.sql | docker exec -i airflow-postgres psql -U airflow airflow

# MLflow 데이터 복원
cat mlflow-backup-20251226.tar.gz | docker exec -i mlflow tar -xzf - -C /

# DAG 파일 복원
tar -xzf dags-backup-20251226.tar.gz -C /
```

### 정리

```bash
# 중지된 컨테이너 제거
docker container prune -f

# 사용하지 않는 이미지 제거
docker image prune -a -f

# 사용하지 않는 볼륨 제거
docker volume prune -f

# 전체 정리 (주의)
docker system prune -a --volumes -f

# MLOps 관련 리소스만 정리
docker compose -f docker-compose-mlops.yml down -v
```

### 로그 관리

```bash
# 오래된 Airflow 로그 삭제 (30일 이상)
find /home/i/work/ai/lakehouse-tick/logs/airflow -type f -mtime +30 -delete

# MLflow 로그 삭제 (30일 이상)
find /home/i/work/ai/lakehouse-tick/logs/mlflow -type f -mtime +30 -delete

# 로그 파일 압축
find /home/i/work/ai/lakehouse-tick/logs -type f -name "*.log" -mtime +7 -exec gzip {} \;
```

---

## 성능 모니터링

### 리소스 사용률

```bash
# 실시간 리소스 모니터링
docker stats mlflow airflow-webserver airflow-scheduler airflow-worker

# 디스크 사용량
docker system df -v | grep -E 'mlflow|airflow'

# 볼륨 크기 확인
docker volume ls --format '{{.Name}}' | grep -E 'mlflow|airflow' | xargs -I {} docker volume inspect {} --format '{{.Name}}: {{.Mountpoint}}'
```

### 성능 메트릭

```bash
# Airflow 실행 통계
docker exec airflow-scheduler airflow dags list-runs --state success | wc -l  # 성공
docker exec airflow-scheduler airflow dags list-runs --state failed | wc -l   # 실패

# MLflow 실험 수
curl -s "http://localhost:5000/api/2.0/mlflow/experiments/search?max_results=1000" | grep -c experiment_id

# PostgreSQL 연결 수
docker exec airflow-postgres psql -U airflow -d airflow -c "SELECT count(*) FROM pg_stat_activity;"

# Redis 메모리 사용량
docker exec airflow-redis redis-cli INFO memory | grep used_memory_human
```

---

## 빠른 참조 치트시트

### 매일 사용하는 명령어

```bash
# 1. 스택 시작
docker compose -f docker-compose-mlops.yml up -d

# 2. DAG 실행
docker exec airflow-scheduler airflow dags trigger ml_pipeline_end_to_end

# 3. 실행 상태 확인
docker exec airflow-scheduler airflow dags list-runs -d ml_pipeline_end_to_end

# 4. 로그 확인
docker compose -f docker-compose-mlops.yml logs -f airflow-worker

# 5. 스택 중지
docker compose -f docker-compose-mlops.yml stop
```

### 트러블슈팅 시 사용하는 명령어

```bash
# 1. 서비스 상태
docker compose -f docker-compose-mlops.yml ps

# 2. 로그 확인
docker compose -f docker-compose-mlops.yml logs --tail=100 airflow-scheduler

# 3. 컨테이너 재시작
docker compose -f docker-compose-mlops.yml restart airflow-worker

# 4. 네트워크 테스트
docker exec airflow-worker curl http://mlflow:5000/health

# 5. Python 환경 확인
docker exec airflow-worker pip list | grep mlflow
```

---

**작성**: 2025-12-26
**버전**: 1.0
**관련 문서**:
- [QUICK_START.md](./QUICK_START.md) - 빠른 시작
- [MLOPS_WORKFLOW_GUIDE.md](./MLOPS_WORKFLOW_GUIDE.md) - 상세 가이드
