# 실행 계획 (Execution Plan)

## 📋 목차

1. [단계별 실행 계획](#단계별-실행-계획)
2. [우선순위](#우선순위)
3. [테스트 체크리스트](#테스트-체크리스트)
4. [롤백 전략](#롤백-전략)
5. [모니터링](#모니터링)

---

## 단계별 실행 계획

### Phase 1: 사전 준비 (1-2시간)

#### 1.1 환경 확인

```bash
# 작업 디렉토리 이동
cd /home/i/work/ai/lakehouse-tick

# 현재 상태 확인
docker compose -f docker-compose-mlops.yml ps

# 백업 생성
cp requirements-airflow.txt requirements-airflow.txt.backup
cp docker-compose-mlops.yml docker-compose-mlops.yml.backup
```

**체크리스트**:
- [ ] Airflow 실행 중
- [ ] MLflow 실행 중
- [ ] 네트워크 연결 확인
- [ ] 백업 완료

#### 1.2 의존성 파일 수정

- `requirements-airflow.txt` 수정 (Traditional ML + DL 라이브러리 추가)
- `docker-compose-mlops.yml` 수정 (리소스 증가)

**확인**:
- [ ] XGBoost, LightGBM 의존성 추가
- [ ] TensorFlow, PyTorch 의존성 추가
- [ ] CPU 제한 변경 (2 → 6)
- [ ] 메모리 제한 변경 (2G → 8G)

---

### Phase 2: Docker 이미지 재빌드 (20-30분)

```bash
# MLOps 스택 중지
docker compose -f docker-compose-mlops.yml down

# Airflow worker 이미지 재빌드 (의존성 설치)
docker compose -f docker-compose-mlops.yml build --no-cache airflow-worker

# 로그 모니터링
docker compose -f docker-compose-mlops.yml up -d
docker compose -f docker-compose-mlops.yml logs -f airflow-worker
```

**확인**:
- [ ] 빌드 성공
- [ ] 라이브러리 설치 완료
- [ ] 모든 컨테이너 running 상태

#### 2.1 라이브러리 설치 확인

```bash
# Worker 컨테이너 접속
docker compose -f docker-compose-mlops.yml exec airflow-worker bash

# 라이브러리 버전 확인
python -c "import xgboost; print(f'XGBoost: {xgboost.__version__}')"
python -c "import lightgbm; print(f'LightGBM: {lightgbm.__version__}')"
python -c "import tensorflow as tf; print(f'TensorFlow: {tf.__version__}')"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
```

---

### Phase 3: Traditional ML DAG 구현 (1-2시간)

#### 3.1 XGBoost DAG 작성

1. 파일 생성: `dags/xgboost_pipeline_dag.py`
2. [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md)의 예제 참고
3. DAG 문법 확인

```bash
docker compose -f docker-compose-mlops.yml exec airflow-worker \
    python /home/i/work/ai/lakehouse-tick/dags/xgboost_pipeline_dag.py
```

**체크리스트**:
- [ ] 파일 생성
- [ ] 문법 체크 통과
- [ ] Airflow UI에서 DAG 인식

#### 3.2 LightGBM DAG 작성

1. 파일 생성: `dags/lightgbm_pipeline_dag.py`
2. XGBoost DAG를 참고하여 작성
3. DAG 문법 확인

**체크리스트**:
- [ ] 파일 생성
- [ ] 문법 체크 통과
- [ ] Airflow UI에서 DAG 인식

#### 3.3 Traditional ML 테스트

Airflow UI (http://localhost:8082):
1. DAG 활성화
2. "Trigger DAG" 클릭
3. 실행 결과 확인

**체크리스트**:
- [ ] XGBoost DAG 실행 성공
- [ ] LightGBM DAG 실행 성공
- [ ] MLflow에 실험 기록됨
- [ ] 메트릭 로깅 확인

---

### Phase 4: Deep Learning DAG 구현 (2-3시간)

#### 4.1 TensorFlow MNIST MLP DAG

1. 파일 생성: `dags/tensorflow_mnist_mlp_dag.py`
2. [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md)의 예제 참고
3. DAG 문법 확인

```bash
docker compose -f docker-compose-mlops.yml exec airflow-worker \
    python /home/i/work/ai/lakehouse-tick/dags/tensorflow_mnist_mlp_dag.py
```

**체크리스트**:
- [ ] 파일 생성
- [ ] 문법 체크 통과
- [ ] Airflow UI에서 DAG 인식

#### 4.2 TensorFlow MNIST CNN DAG

1. 파일 생성: `dags/tensorflow_mnist_cnn_dag.py`
2. MLP DAG를 참고하여 Conv2D 추가
3. DAG 문법 확인

#### 4.3 PyTorch MNIST MLP DAG

1. 파일 생성: `dags/pytorch_mnist_mlp_dag.py`
2. [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md)의 예제 참고
3. DAG 문법 확인

#### 4.4 PyTorch MNIST CNN DAG

1. 파일 생성: `dags/pytorch_mnist_cnn_dag.py`
2. MLP DAG를 참고하여 Conv2D 추가
3. DAG 문법 확인

#### 4.5 Deep Learning 테스트

Airflow UI (http://localhost:8082):
1. 각 DAG 활성화
2. "Trigger DAG" 클릭 (MLP부터 시작)
3. 실행 결과 확인 (시간 소요 예상)

**체크리스트**:
- [ ] TensorFlow MLP DAG 실행 성공 (5-10분 예상)
- [ ] TensorFlow CNN DAG 실행 성공 (20-30분 예상)
- [ ] PyTorch MLP DAG 실행 성공 (5-10분 예상)
- [ ] PyTorch CNN DAG 실행 성공 (20-30분 예상)
- [ ] 모든 메트릭 MLflow에 기록됨

---

### Phase 5: 최적화 및 모니터링 (진행 중)

#### 5.1 성능 분석

MLflow UI에서:
- 각 모델의 학습 곡선 분석
- 메트릭 비교
- 실행 시간 분석

#### 5.2 필요시 조정

- 하이퍼파라미터 조정
- 배치 크기 최적화
- 에포크 수 조정

---

## 우선순위

| 순서 | 모델 | 리소스 | 예상 시간 | 난이도 |
|------|------|--------|----------|--------|
| 1 | XGBoost | 현재 | 5분 | ★☆☆ |
| 2 | LightGBM | 현재 | 5분 | ★☆☆ |
| 3 | TF MNIST MLP | 증가됨 | 10분 | ★★☆ |
| 4 | TF MNIST CNN | 증가됨 | 30분 | ★★☆ |
| 5 | PyTorch MLP | 증가됨 | 10분 | ★★☆ |
| 6 | PyTorch CNN | 증가됨 | 30분 | ★★★ |

---

## 테스트 체크리스트

### XGBoost 테스트 체크리스트

```
[ ] DAG 생성
[ ] DAG 문법 확인
[ ] Airflow UI에서 DAG 표시
[ ] DAG 수동 실행
[ ] Task 모두 완료
[ ] MLflow에 실험 기록
[ ] 정확도 > 0.85
[ ] 메트릭 로깅 확인
```

### LightGBM 테스트 체크리스트

```
[ ] DAG 생성
[ ] DAG 문법 확인
[ ] Airflow UI에서 DAG 표시
[ ] DAG 수동 실행
[ ] Task 모두 완료
[ ] MLflow에 실험 기록
[ ] 정확도 > 0.87
[ ] 메트릭 로깅 확인
[ ] XGBoost와 비교 분석
```

### TensorFlow MNIST MLP 테스트 체크리스트

```
[ ] DAG 생성
[ ] DAG 문법 확인
[ ] Airflow UI에서 DAG 표시
[ ] DAG 수동 실행
[ ] Task 모두 완료 (예상: 5-10분)
[ ] MLflow에 실험 기록
[ ] 정확도 > 0.95
[ ] 메트릭 로깅 확인
[ ] Loss 곡선 확인 (수렴 여부)
```

### TensorFlow MNIST CNN 테스트 체크리스트

```
[ ] DAG 생성
[ ] DAG 문법 확인
[ ] Airflow UI에서 DAG 표시
[ ] DAG 수동 실행
[ ] Task 모두 완료 (예상: 20-30분)
[ ] MLflow에 실험 기록
[ ] 정확도 > 0.98
[ ] 메트릭 로깅 확인
[ ] MLP와 비교 분석
```

### PyTorch 테스트 체크리스트

```
[ ] MLP DAG 생성
[ ] MLP DAG 실행 성공
[ ] MLP 정확도 > 0.95
[ ] CNN DAG 생성
[ ] CNN DAG 실행 성공
[ ] CNN 정확도 > 0.98
[ ] TensorFlow와 비교 분석
```

---

## 롤백 전략

### 문제 상황별 대응

#### 상황 1: 이미지 빌드 실패

```bash
# 백업 파일로 되돌리기
cp requirements-airflow.txt.backup requirements-airflow.txt
cp docker-compose-mlops.yml.backup docker-compose-mlops.yml

# 이전 이미지 사용
docker compose -f docker-compose-mlops.yml down
docker compose -f docker-compose-mlops.yml up -d
```

#### 상황 2: DAG 문법 오류

```bash
# DAG 파일 삭제
rm /home/i/work/ai/lakehouse-tick/dags/problematic_dag.py

# Airflow 재시작
docker compose -f docker-compose-mlops.yml restart airflow-scheduler
docker compose -f docker-compose-mlops.yml restart airflow-worker
```

#### 상황 3: 메모리 부족

```yaml
# docker-compose-mlops.yml 수정
airflow-worker:
  deploy:
    resources:
      limits:
        memory: 10G  # 더 증가
```

#### 상황 4: 학습 시간 초과

```python
# DAG의 default_args 수정
default_args = {
    'execution_timeout': timedelta(hours=4),  # 4시간으로 증가
}
```

---

## 모니터링

### Airflow UI 모니터링

**URL**: http://localhost:8082

체크 포인트:
- DAG 리스트에서 모든 DAG 표시 확인
- 각 DAG의 "Graph View"에서 task 의존성 확인
- "Tree View"에서 실행 이력 확인
- Task 로그에서 오류 확인

### MLflow UI 모니터링

**URL**: http://localhost:5000

체크 포인트:
- Experiments: 모든 실험이 기록되는지 확인
- Runs: 각 run의 파라미터와 메트릭 확인
- Models: 모델 등록 여부 확인
- Artifacts: 모델 파일 저장 확인

### 로그 모니터링

```bash
# 실시간 로그 확인
docker compose -f docker-compose-mlops.yml logs -f airflow-worker

# 특정 키워드로 필터링
docker compose -f docker-compose-mlops.yml logs airflow-worker | grep -i "error\|✅"

# MLflow 로그
docker compose -f docker-compose-mlops.yml logs -f mlflow
```

### 성능 모니터링

```bash
# Docker 리소스 사용량 확인
docker stats

# 디스크 공간 확인
df -h

# 메모리 사용량 확인
free -h
```

---

## 예상 일정

| Phase | 소요 시간 | 예상 시작일 | 예상 완료일 |
|-------|----------|-----------|-----------|
| 1. 사전 준비 | 1-2시간 | Day 1 | Day 1 |
| 2. Docker 재빌드 | 20-30분 | Day 1 | Day 1 |
| 3. Traditional ML | 1-2시간 | Day 1 | Day 1 |
| 4. Deep Learning | 2-3시간 | Day 2 | Day 2-3 |
| 5. 최적화 및 모니터링 | 진행 중 | Day 3 | - |

---

## 성공 기준

모든 DAG가 다음 조건을 만족하면 성공:

1. **DAG 실행**
   - [ ] Airflow UI에서 DAG 인식
   - [ ] 수동 실행 가능
   - [ ] 모든 Task 완료

2. **MLflow 통합**
   - [ ] 실험 기록됨
   - [ ] 파라미터 로깅됨
   - [ ] 메트릭 로깅됨
   - [ ] 모델 등록됨

3. **성능**
   - [ ] XGBoost/LightGBM: 정확도 > 85%
   - [ ] TensorFlow/PyTorch MLP: 정확도 > 95%
   - [ ] TensorFlow/PyTorch CNN: 정확도 > 98%

4. **안정성**
   - [ ] 오류 발생 없음
   - [ ] 타임아웃 없음
   - [ ] 메모리 부족 없음

---

**다음**: [README로 돌아가기 →](README.md)
