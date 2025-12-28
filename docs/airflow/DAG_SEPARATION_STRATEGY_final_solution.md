# DAG 분리 전략 (Final Solution, 2025 현업 운영 기준)

이 문서는 `MNIST(CNN)`, `CIFAR-10(CNN)`, `Tick data`, `가정집 전력(LightGBM)` 4개 학습 워크플로우를 **Airflow + MLflow**로 운영할 때, 2025년 현업에서 가장 흔하고 확장/운영에 강한 “정답 패턴”을 하나로 정리한 최종 가이드입니다.

---

## 1) 결론 (의사결정 요약)

### 1.1 DAG는 “4개 분리”가 기본값
다음 네 가지는 **스케줄/리소스/데이터 준비/실패 영향(Blast Radius)/소유권(Ownership)** 이 근본적으로 달라, 운영 단계에서는 DAG를 분리하는 것이 표준에 가깝습니다.

- `mnist_cnn_training` (실험/튜토리얼, GPU)
- `cifar10_cnn_training` (실험/모델 고도화, GPU)
- `tick_model_training` (시계열/금융, 대용량/증분/백필 민감)
- `power_lgbm_training` (정형/시계열 피처 + CPU 중심)

> 예외: MNIST/CIFAR-10은 “같은 스케줄·같은 GPU 정책·같은 배포 단위”라면 하나의 템플릿에서 **DAG는 2개(서로 다른 `dag_id`)로 생성하되 코드만 공통화**하는 패턴이 가장 흔합니다.

### 1.2 파일은 1~4개 모두 가능 (DAG `dag_id`가 운영 단위)
- **DAG(= `dag_id`)** 가 모니터링/재시도/권한/알림의 기본 단위입니다.
- **파일**은 코드 배치 방식일 뿐이라서, 4개 DAG를 4개 파일로 둘 수도 있고, Factory 패턴으로 1개 파일에서 4개 DAG를 만들어도 됩니다.

현업에서 많이 쓰는 2가지 패턴:
- **Pattern A (권장 시작점)**: DAG 파일을 분리(직관적, 디버깅 쉬움)
- **Pattern B (확장형)**: Factory + 설정(config) 기반으로 여러 DAG를 동적 생성(일관성/확장성 최고)

---

## 2) 왜 분리하는가 (핵심 이유 5가지)

1. **스케줄/트리거가 다름**: 실험성(수동/주간) vs 일배치 vs 준실시간/증분 등
2. **리소스 요구가 다름**: GPU(CNN) vs CPU(LightGBM) vs I/O·클러스터(Spark/대용량)
3. **실패 격리**: Tick 파이프라인 장애가 이미지 실험 학습을 멈추면 운영이 불편해짐
4. **백필(backfill) 단위가 다름**: Tick은 구간 재처리가 잦고 비용이 큼
5. **Ownership/배포 단위가 다름**: 팀/책임/라이브러리/컨테이너 이미지가 달라지는 경우가 많음

---

## 3) 4개 케이스 권장 운영 매핑 (표준 템플릿)

| 케이스 | 권장 DAG ID | 스케줄 예시 | 리소스 격리 | 실행 방식(권장) | MLflow 권장 |
|---|---|---:|---|---|---|
| MNIST(CNN) | `mnist_cnn_training` | `None`(수동) 또는 주 1회 | `pool=gpu_pool`, `queue=gpu_queue` | `KubernetesPodOperator`(GPU) 또는 GPU worker | Experiment: `mnist-cnn`, Model: `mnist_cnn` |
| CIFAR-10(CNN) | `cifar10_cnn_training` | `None`(수동) 또는 주 1회 | `pool=gpu_pool`, `queue=gpu_queue` | `KubernetesPodOperator`(GPU) | Experiment: `cifar10-cnn`, Model: `cifar10_cnn` |
| Tick data | `tick_model_training` | 일 1회(장마감 후) 또는 주 1회 | `pool=high_priority_cpu`, `queue=realtime_queue` | 데이터 준비는 Spark(배치), 학습은 별도 job/컨테이너 | Experiment: `tick-production`, Model: `tick_model` |
| 전력(LightGBM) | `power_lgbm_training` | 일 1회(새벽) | `pool=default_pool`, `queue=batch_queue` | `PythonOperator` + 외부 스크립트/컨테이너 | Experiment: `power-forecast`, Model: `power_lgbm` |

핵심은 “모델 종류”보다 **워크로드 성격(리소스·주기·운영 위험)** 에 맞춰 DAG를 분리하고, 코드는 템플릿/모듈로 공유하는 것입니다.

---

## 4) 공통 설계 원칙 (유지보수/확장성의 핵심)

### 4.1 DAG는 오케스트레이션만 담당
- DAG 파일 내부에 학습/전처리 “비즈니스 로직”을 길게 넣지 않습니다.
- 실제 학습/전처리는 `python` 패키지, `scripts/`, 또는 컨테이너 이미지 내부 엔트리포인트로 분리합니다.

### 4.2 공통 기능은 “DAG 밖 모듈”로
공통으로 반복되는 부분은 반드시 재사용 레이어로 끌어올립니다.
- MLflow 설정/로깅(파라미터, 메트릭, 아티팩트, 모델 등록)
- 데이터 로드/검증/스키마 체크
- 알림(on-failure), SLA, 공통 태그/네이밍 규칙
- 공통 “train → eval → (조건부) register” 흐름

### 4.3 리소스 격리: pools/queues/priority를 표준화
GPU/CPU/실시간성 워크로드가 섞이는 순간, 아래는 “선택”이 아니라 “필수”에 가깝습니다.
- `pool`: `gpu_pool`, `high_priority_cpu`, `default_pool` 등으로 슬롯 제한
- `queue`: 워커/노드 분리(Celery queue 또는 K8s 노드풀)
- `priority_weight`: Tick 같은 업무 우선순위 반영
- `task_concurrency` / `max_active_runs`: 대형 학습의 동시 실행 제한

---

## 5) Pattern A vs Pattern B (파일 구조 선택)

### Pattern A: DAG 파일 분리 (직관적, 추천 시작점)
소규모~중규모 팀에서 가장 무난합니다.

```text
dags/
  ml_pipeline_dag.py              # (기존) 데이터 파이프라인
  ml_mnist_cnn_dag.py             # mnist_cnn_training
  ml_cifar10_cnn_dag.py           # cifar10_cnn_training
  ml_tick_model_dag.py            # tick_model_training
  ml_power_lgbm_dag.py            # power_lgbm_training
  common/
    mlflow_utils.py
    config.py
    alerts.py
    registry.py
  scripts/
    train_mnist.py
    train_cifar10.py
    train_tick.py
    train_power_lgbm.py
```

장점
- 읽기/리뷰/디버깅이 쉬움
- ownership(책임) 분리가 명확

단점
- 공통 로직을 모듈로 끌어올리지 않으면 중복이 쌓임(그래서 `common/`이 핵심)

### Pattern B: Factory + 설정 기반 (확장/관리 “최고”)
DAG가 10개 이상으로 늘어나거나, 템플릿이 확실할 때 강력합니다.

```python
# dags/model_training_factory_dags.py (예시 스케치)
TRAINING_CONFIGS = [
  {"dag_id": "mnist_cnn_training", "kind": "cnn", "dataset": "mnist", "pool": "gpu_pool"},
  {"dag_id": "cifar10_cnn_training", "kind": "cnn", "dataset": "cifar10", "pool": "gpu_pool"},
  {"dag_id": "tick_model_training", "kind": "timeseries", "dataset": "tick", "pool": "high_priority_cpu"},
  {"dag_id": "power_lgbm_training", "kind": "lgbm", "dataset": "power", "pool": "default_pool"},
]

for cfg in TRAINING_CONFIGS:
  globals()[cfg["dag_id"]] = create_ml_training_dag(**cfg)
```

장점
- 설정만 추가하면 새 DAG를 빠르게 확장
- 공통 정책(태그/알림/MLflow 규칙)을 중앙에서 강제 가능

단점
- 동적 생성 구조가 익숙하지 않으면 디버깅이 어려울 수 있음
- 특수 케이스(특정 DAG만 다른 태스크 구성)가 늘면 복잡도가 증가

현업 팁
- “Factory는 DAG 수가 늘 때” 도입하되, 처음부터 무리해서 올인하지 않습니다.
- 대신 **공통 모듈부터 먼저** 깔고, 이후 자연스럽게 Factory로 리팩터링하는 흐름이 안전합니다.

---

## 6) Tick data는 특별 취급 (현업 현실)

Tick은 “Airflow로 실시간 처리”를 목표로 하면 운영 난이도가 급상승합니다.

권장 분담
- **실시간 수집/전송**: Kafka/Kinesis 등 스트리밍 계층
- **Airflow 역할**: 배치 롤업(예: 1시간/1일 집계), 피처 생성, 재학습 트리거, 모델 등록

운영 포인트
- 증분 처리/데이터 윈도우(시간 파티션) 기준을 명확히 문서화
- 백필 전략(기간 지정 재처리)과 비용 통제를 미리 정의
- 데이터 준비 완료를 기다리는 **Sensor/이벤트 기반 트리거**를 고려(무작정 시간 기반 스케줄만으로 해결하지 않기)

---

## 7) 데이터 파이프라인과 학습 DAG의 연결(권장)

이미 레포에 `dags/ml_pipeline_dag.py` 같은 데이터 레이어 파이프라인이 있다면, 학습 DAG는 다음 중 하나로 “데이터 준비 완료”를 보장합니다.

1) **ExternalTaskSensor**: 데이터 DAG의 특정 태스크(Gold/Features 완료)를 기다린 뒤 학습 시작
2) **Airflow Datasets(가능한 환경일 때)**: “데이터셋 업데이트 이벤트”로 학습 DAG를 트리거

원칙
- 데이터 적재/정제 DAG와 모델 학습 DAG는 분리 유지(장애 격리 + 백필 전략 분리)
- 학습 DAG는 “입력 데이터 버전(파티션/스냅샷)”을 MLflow에 반드시 기록(재현성)

---

## 8) 운영 체크리스트 (배포 전 필수)

- **리소스 격리**
  - [ ] GPU 작업은 `gpu_pool`/`gpu_queue`로 격리
  - [ ] Tick은 우선순위/동시성 제한을 가장 보수적으로
- **재현성**
  - [ ] 입력 데이터 버전(날짜 파티션, 스냅샷, Git SHA)을 MLflow param으로 로깅
  - [ ] 학습 코드/이미지 버전(태그)을 MLflow param으로 로깅
- **안정성**
  - [ ] 태스크는 idempotent(재실행해도 안전)하게 설계
  - [ ] 큰 학습은 `execution_timeout`/`retries`/`retry_delay`를 합리적으로 설정
- **모델 레지스트리**
  - [ ] “자동 Production 승격”은 기본 비활성(임계값+승인 프로세스 권장)
- **알림/SLA**
  - [ ] on-failure 알림(예: Slack)과 SLA(지연 허용치) 정의

---

## 9) 다음 액션 (이 레포 기준으로 빠르게 진행하려면)

1) 4개 DAG의 `dag_id`, 스케줄, pool/queue 정책을 확정
2) `dags/common/`에 MLflow/알림/공통 config 모듈을 먼저 만든 뒤
3) Pattern A로 4개 DAG를 만들고, DAG 수가 늘면 Pattern B(Factory)로 리팩터링

