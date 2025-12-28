# use_case_mnist: MNIST CNN 학습 DAG 생성/실행 가이드 (train_with_docker)

이 문서는 이 레포에서 **MNIST CNN 학습 파이프라인을 Airflow DAG로 추가하고**, 실제로 **Airflow에서 실행 성공**시키는 방법을 정리합니다.

핵심 아이디어:
- Airflow 컨테이너(웹서버/스케줄러/워커)에 TensorFlow를 `pip install`로 넣지 않고,
- 학습만 `tensorflow/tensorflow` Docker 이미지에서 수행하도록 해서 **Airflow 이미지/의존성을 가볍게 유지**합니다.

---

## 1) 구성 요약

### DAG
- DAG 파일: `dags/ml_mnist_cnn_dag.py`
- DAG ID: `mnist_cnn_training`
- Task 구성
  - `train_mnist_tf`: `DockerOperator`로 `tensorflow/tensorflow:2.15.0` 컨테이너에서 MNIST를 CPU로 짧게 학습(스모크 테스트)
  - `log_to_mlflow`: `PythonOperator`로 결과(JSON)를 파싱해 MLflow에 메트릭 기록

### 왜 DockerOperator인가? (final_solution 정렬)
- Airflow는 “오케스트레이션”만 담당하고, 무거운 DL 런타임(TF/PyTorch)은 **전용 학습 컨테이너**가 담당합니다.
- 이는 `docs/airflow/DAG_SEPARATION_STRATEGY_final_solution.md`의 원칙(“DAG는 오케스트레이션만”, “공통 기능 모듈화”, “리소스/의존성 격리”)에 가장 가깝습니다.
- 운영 확장 시에도 같은 패턴으로 **PyTorch/CIFAR10 등 다른 워크로드**를 쉽게 추가할 수 있습니다.

---

## 2) 사전 조건

### 2.1 Docker / Docker Compose
호스트에서 다음이 가능해야 합니다.
- `docker` 실행 가능
- `docker compose` 실행 가능

### 2.2 Airflow + MLflow 스택이 올라와 있어야 함
이 레포는 `docker-compose-mlops.yml`로 Airflow/MLflow를 올립니다.

```bash
docker compose -f docker-compose-mlops.yml up -d
docker compose -f docker-compose-mlops.yml ps
```

Airflow UI: `http://localhost:8082`  
MLflow UI: `http://localhost:5000`

### 2.3 Airflow Worker가 Docker 실행 가능해야 함 (중요)
`DockerOperator`는 **Airflow worker 컨테이너 안에서 “또 다른 Docker 컨테이너”를 실행**합니다.
따라서 worker가 호스트 Docker 데몬에 접근해야 합니다.

이 레포에서는 `docker-compose-mlops.yml`에서 아래 2가지를 추가했습니다.
- `/var/run/docker.sock` 마운트
- `group_add`로 docker 그룹 권한 부여(기본값 `989`, 필요 시 `DOCKER_GID`로 변경)

파일 위치: `docker-compose-mlops.yml`의 `airflow-worker` 서비스

변경 후 worker만 재기동:
```bash
docker compose -f docker-compose-mlops.yml up -d --no-deps --force-recreate airflow-worker
```

---

## 3) TensorFlow 이미지 준비

MNIST 학습은 `tensorflow/tensorflow:2.15.0` 이미지를 사용합니다.

```bash
docker pull tensorflow/tensorflow:2.15.0
```

---

## 4) DAG가 Airflow에 “바로 적용”되는 이유

`docker-compose-mlops.yml`에서 다음처럼 **호스트 폴더를 컨테이너에 마운트**합니다.

- `./dags:/opt/airflow/dags`

즉, 로컬에서 `dags/ml_mnist_cnn_dag.py`를 수정/저장하면 컨테이너의 `/opt/airflow/dags`에도 즉시 반영되고,
Airflow scheduler가 이를 스캔하여 DAG를 로드합니다.

---

## 5) 실행 방법 (CLI)

### 5.1 DAG 존재 확인
```bash
docker exec airflow-scheduler bash -lc \
  "airflow dags list --output json | grep -F '\"dag_id\": \"mnist_cnn_training\"' || true"
```

### 5.2 DAG 활성화(unpause)
```bash
docker exec airflow-scheduler bash -lc "airflow dags unpause mnist_cnn_training"
```

### 5.3 DAG 수동 실행(trigger)
```bash
RUN_ID="manual__$(date -u +%Y%m%dT%H%M%S)"
docker exec airflow-scheduler bash -lc "airflow dags trigger mnist_cnn_training --run-id ${RUN_ID}"
```

### 5.4 상태 확인
```bash
docker exec airflow-scheduler bash -lc "airflow dags list-runs -d mnist_cnn_training --output json"
```

특정 run의 task 상태:
```bash
docker exec airflow-scheduler bash -lc \
  "airflow tasks states-for-dag-run mnist_cnn_training ${RUN_ID}"
```

---

## 6) 실행 방법 (Airflow UI)

1. Airflow UI 접속: `http://localhost:8082` (기본 `admin/admin`)
2. `mnist_cnn_training` DAG를 켠다(토글)
3. “Trigger DAG” 버튼으로 실행
4. Graph/Task에서 `train_mnist_tf` → `log_to_mlflow` 순으로 성공 확인

---

## 7) MLflow 결과 확인

이 DAG는 `mnist-cnn` experiment에 메트릭을 기록합니다.

### 7.1 MLflow UI에서 확인
`http://localhost:5000` → Experiments → `mnist-cnn`

### 7.2 CLI로 확인(컨테이너 내부에서 조회)
```bash
docker exec airflow-scheduler bash -lc "python - <<'PY'
import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_tracking_uri('http://mlflow:5000')
client = MlflowClient()
exp = mlflow.get_experiment_by_name('mnist-cnn')
print('experiment_id', None if exp is None else exp.experiment_id)
if exp is None:
    raise SystemExit(0)

runs = client.search_runs([exp.experiment_id], order_by=['attributes.start_time DESC'], max_results=1)
run = runs[0]
print('run_id', run.info.run_id)
print('run_name', run.data.tags.get('mlflow.runName'))
print('params', run.data.params)
print('metrics', run.data.metrics)
PY"
```

---

## 8) 구현 디테일(중요 포인트)

### 8.1 학습이 “CPU 스모크 테스트”인 이유
`dags/ml_mnist_cnn_dag.py`에서 학습을 빨리 끝내기 위해 다음처럼 제한합니다.
- train 샘플 5,000개, test 1,000개
- epoch 1

운영/실험 목적에 맞게 `epochs`, 샘플 수, 모델 구조를 조정하세요.

### 8.2 컨테이너 네트워크
현재 `train_mnist_tf`는 `network_mode="bridge"` 입니다.
- 이 예제는 “학습 컨테이너가 MLflow로 직접 통신”하지 않기 때문에 문제 없습니다.
- 만약 학습 컨테이너에서 `mlflow.tensorflow.autolog()` 같은 걸로 직접 로깅하려면,
  학습 컨테이너가 `mlflow` 호스트명에 접근 가능하도록 네트워크를 조정해야 합니다(예: compose 네트워크 사용).

---

## 9) 트러블슈팅

### DAG가 UI에 안 보일 때
- 스케줄러 로그에서 import error 확인: `docker compose -f docker-compose-mlops.yml logs -f airflow-scheduler`
- 파일이 실제로 컨테이너에 마운트됐는지 확인: `docker exec airflow-scheduler ls -la /opt/airflow/dags`

### DockerOperator가 “Docker 데몬에 접근 불가”로 실패할 때
대부분 아래 둘 중 하나입니다.
- `/var/run/docker.sock`가 worker에 마운트되지 않음
- docker.sock 권한(그룹)이 맞지 않음 → `DOCKER_GID`를 환경에 맞게 지정

호스트에서 docker 그룹 GID 확인(리눅스/WSL):
```bash
getent group docker
```

그 값을 `.env`에 추가(예: `DOCKER_GID=989`) 후 worker 재기동:
```bash
docker compose -f docker-compose-mlops.yml up -d --no-deps --force-recreate airflow-worker
```
