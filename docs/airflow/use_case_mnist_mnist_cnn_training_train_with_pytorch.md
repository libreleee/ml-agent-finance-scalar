# use_case_mnist: MNIST CNN 학습 DAG 생성/실행 가이드 (train_with_pytorch)

이 문서는 MNIST CNN 학습을 **Airflow Worker 컨테이너에서 PyTorch를 직접 import**하여 학습하는 방식의 예제를 정리합니다.

> 권장 관점: `docs/airflow/DAG_SEPARATION_STRATEGY_final_solution.md`의 “오케스트레이션/학습 런타임 분리” 원칙상, 운영에는 Docker/K8s 실행 방식이 더 안전합니다.  
> 이 문서는 PyTorch 버전 구현/의존성/운영 포인트를 이해하기 위한 비교용 가이드입니다.

---

## 1) final_solution 관점에서의 위치

`docs/airflow/DAG_SEPARATION_STRATEGY_final_solution.md` 핵심 원칙:
- DAG는 워크플로우 단위로 분리하고, 장애/스케줄/리소스를 격리한다.
- 학습 런타임(TF/PyTorch)은 Airflow 이미지와 분리하는 편이 운영에 유리하다.

이 문서 방식(train_with_pytorch):
- ✅ DAG 분리/MLflow 로깅은 그대로 적용
- ⚠️ PyTorch/torchvision을 Airflow 컨테이너에 직접 설치해야 하므로 이미지가 커지고(특히 wheel), 업그레이드/충돌 리스크가 증가

---

## 2) 구성 요약

### DAG
- DAG 파일(신규): `dags/ml_mnist_cnn_pytorch_native_dag.py`
- DAG ID(신규): `mnist_cnn_training_pytorch_native`
- Task 구성
  - `train_mnist_torch_native`: `PythonOperator`로 PyTorch 학습을 직접 실행(CPU 스모크 테스트)
  - `log_to_mlflow`: MLflow에 메트릭 기록

---

## 3) 사전 조건

### 3.1 Airflow 컨테이너에 PyTorch 설치 필요
이 방식은 Airflow worker 내부에서 `import torch` / `import torchvision`이 성공해야 합니다.

선택지 A(가장 간단, 비권장 운영): `_PIP_ADDITIONAL_REQUIREMENTS`로 설치  
`docker-compose-mlops.yml`의 webserver/scheduler/worker에 예시:

```yaml
_PIP_ADDITIONAL_REQUIREMENTS: mlflow boto3 scikit-learn numpy torch==2.1.0 torchvision==0.16.0
```

> 주의: PyTorch는 플랫폼/파이썬 버전에 따라 wheel 크기가 크고 설치 시간이 길 수 있습니다.

선택지 B(권장 운영): 커스텀 Airflow 이미지 빌드
- 빌드 타임에 torch/torchvision 설치(재현성/부팅속도 개선)

---

## 4) 실행 방법

### 4.1 DAG 로드 확인
```bash
docker exec airflow-scheduler bash -lc \
  "airflow dags list --output json | grep -F '\"dag_id\": \"mnist_cnn_training_pytorch_native\"' || true"
```

### 4.2 DAG 활성화 및 트리거
```bash
docker exec airflow-scheduler bash -lc "airflow dags unpause mnist_cnn_training_pytorch_native"

RUN_ID="manual__$(date -u +%Y%m%dT%H%M%S)"
docker exec airflow-scheduler bash -lc "airflow dags trigger mnist_cnn_training_pytorch_native --run-id ${RUN_ID}"
```

### 4.3 상태 확인
```bash
docker exec airflow-scheduler bash -lc "airflow dags list-runs -d mnist_cnn_training_pytorch_native --output json"
docker exec airflow-scheduler bash -lc "airflow tasks states-for-dag-run mnist_cnn_training_pytorch_native ${RUN_ID}"
```

---

## 5) MLflow 결과 확인

이 DAG는 `mnist-cnn` experiment에 기록합니다(다른 구현들과 비교 가능).

- MLflow UI: `http://localhost:5000` → experiment `mnist-cnn`

---

## 6) 트러블슈팅

### `ModuleNotFoundError: No module named 'torch'` 또는 `torchvision`
- Airflow worker에 torch/torchvision이 설치되지 않은 상태입니다.
- `_PIP_ADDITIONAL_REQUIREMENTS` 또는 커스텀 이미지로 해결하세요.

### MNIST 데이터 다운로드 경로 문제
- PyTorch 예제는 `torchvision.datasets.MNIST`를 사용하며 기본적으로 데이터를 다운로드합니다.
- 컨테이너에서 쓸 수 있는 경로(예: `/tmp/mnist-data`)를 사용하도록 DAG 코드에서 지정합니다.

