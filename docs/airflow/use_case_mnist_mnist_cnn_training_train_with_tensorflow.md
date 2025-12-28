# use_case_mnist: MNIST CNN 학습 DAG 생성/실행 가이드 (train_with_tensorflow)

이 문서는 MNIST CNN 학습을 **DockerOperator 없이**, Airflow Worker 컨테이너에서 **TensorFlow/Keras를 직접 import**하여 학습하는 방식의 예제를 정리합니다.

> 권장 관점: `docs/airflow/DAG_SEPARATION_STRATEGY_final_solution.md`의 “오케스트레이션/학습 런타임 분리” 원칙상, 운영(특히 GPU/대규모)에는 `train_with_docker`(또는 K8s Pod 실행)가 더 안전합니다.  
> 이 문서는 “직접 학습 방식이 어떤 비용/리스크를 가지는지”를 이해하기 위한 비교용/교육용 가이드입니다.

---

## 1) final_solution 관점에서의 위치

`docs/airflow/DAG_SEPARATION_STRATEGY_final_solution.md` 핵심 원칙:
- DAG는 워크플로우 단위로 분리하고(`mnist_cnn_training` 등), 장애/스케줄/리소스를 격리한다.
- DAG는 오케스트레이션만 담당하고, 학습 런타임은 컨테이너/별도 실행환경으로 분리하는 편이 운영에 유리하다.

이 문서 방식(train_with_tensorflow):
- ✅ DAG 분리/MLflow 로깅은 그대로 적용
- ⚠️ 학습 런타임을 Airflow 이미지에 직접 넣기 때문에 **의존성 충돌/이미지 비대화/업그레이드 어려움**이 발생할 수 있음

---

## 2) 구성 요약

### DAG
- DAG 파일(신규): `dags/ml_mnist_cnn_tf_native_dag.py`
- DAG ID(신규): `mnist_cnn_training_tf_native`
- Task 구성
  - `train_mnist_tf_native`: `PythonOperator`로 TF/Keras 학습을 직접 실행(CPU 스모크 테스트)
  - `log_to_mlflow`: MLflow에 메트릭 기록

---

## 3) 사전 조건

### 3.1 Airflow 컨테이너에 TensorFlow 설치 필요
이 방식은 Airflow worker 내부에서 `import tensorflow as tf`가 성공해야 합니다.

선택지 A(가장 간단, 비권장 운영): `_PIP_ADDITIONAL_REQUIREMENTS`로 설치  
`docker-compose-mlops.yml`의 webserver/scheduler/worker에 아래처럼 TensorFlow를 추가:

```yaml
_PIP_ADDITIONAL_REQUIREMENTS: mlflow boto3 scikit-learn numpy tensorflow==2.15.0
```

변경 후 재기동:
```bash
docker compose -f docker-compose-mlops.yml up -d --force-recreate airflow-webserver airflow-scheduler airflow-worker
```

선택지 B(권장 운영): 커스텀 Airflow 이미지 빌드
- `apache/airflow:2.8.0-python3.11` 기반 Dockerfile을 만들고
- `pip install tensorflow==2.15.0`를 이미지 빌드 타임에 수행  
→ 런타임 설치보다 재현성과 속도가 좋습니다.

---

## 4) 실행 방법

### 4.1 DAG 로드 확인
```bash
docker exec airflow-scheduler bash -lc \
  "airflow dags list --output json | grep -F '\"dag_id\": \"mnist_cnn_training_tf_native\"' || true"
```

### 4.2 DAG 활성화(unpause) 및 트리거
```bash
docker exec airflow-scheduler bash -lc "airflow dags unpause mnist_cnn_training_tf_native"

RUN_ID="manual__$(date -u +%Y%m%dT%H%M%S)"
docker exec airflow-scheduler bash -lc "airflow dags trigger mnist_cnn_training_tf_native --run-id ${RUN_ID}"
```

### 4.3 상태 확인
```bash
docker exec airflow-scheduler bash -lc "airflow dags list-runs -d mnist_cnn_training_tf_native --output json"
docker exec airflow-scheduler bash -lc "airflow tasks states-for-dag-run mnist_cnn_training_tf_native ${RUN_ID}"
```

---

## 5) MLflow 결과 확인

이 DAG는 `mnist-cnn` experiment에 기록합니다(기존 Docker 버전과 동일).

- MLflow UI: `http://localhost:5000` → experiment `mnist-cnn`

---

## 6) 트러블슈팅

### `ModuleNotFoundError: No module named 'tensorflow'`
- Airflow worker에 TensorFlow가 설치되지 않은 상태입니다.
- `_PIP_ADDITIONAL_REQUIREMENTS`를 늘리거나, 커스텀 이미지로 해결하세요.

### 컨테이너 시작이 너무 느려짐
- `_PIP_ADDITIONAL_REQUIREMENTS`로 TensorFlow를 런타임 설치하면 초기 부팅이 매우 느릴 수 있습니다.
- 운영에서는 커스텀 이미지 빌드 또는 Docker/K8s 실행 방식이 더 적합합니다.

