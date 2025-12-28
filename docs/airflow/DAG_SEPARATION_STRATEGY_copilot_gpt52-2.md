# DAG 분리 전략 (현업 관점)

Airflow + MLflow 조합 기준으로 현업에서 가장 흔한 접근은 다음과 같습니다:

- **DAG는 워크플로우 단위로 분리**(각 워크플로우가 별도의 `dag_id`)합니다.
- **파일 구성은 팀 스타일에 따름**: DAG가 4개라 해도 파일은 1~4개로 구성할 수 있습니다(Factory 패턴으로 한 파일에서 여러 DAG 생성도 흔함).
- **공통 코드는 DAG 밖(모듈/패키지)**으로 분리하여, DAG는 오케스트레이션만 담당하도록 합니다.

요약: 작업이 4개라면 보통 DAG도 4개, 파일 구성은 팀/규모/유지보수 정책에 따라 결정합니다.

---

## 왜 DAG를 분리하나? (주요 이유 5가지)

1. **스케줄/트리거가 다름**
   - MNIST/CIFAR-10: 실험성(수동 혹은 야간 실행)
   - Tick: 빈번한 증분 처리 및 실시간/준실시간 요구 가능
   - 전력 데이터: 일/주/월 단위 배치

2. **리소스 요구가 다름**
   - CNN: GPU·장시간 학습, TensorFlow/PyTorch 의존
   - LightGBM: CPU 중심
   - Tick: I/O·피처 업데이트 중심
   - → 큐/Pool/우선순위 정책으로 분리 운용 권장

3. **실패 격리**
   - 하나의 파이프라인 실패로 인해 다른 모델 학습이 영향을 받지 않도록 분리

4. **재처리(backfill) 단위가 다름**
   - Tick: 특정 구간 단위 재처리
   - 전력: 일 단위 재처리 등

5. **변경/배포 책임(Ownership)이 다름**
   - 모델·데이터 소유자가 다르면 같은 DAG에 합쳐두는 것이 충돌 지점이 됨

---

## 파일을 4개로 나누는 것이 표준인가?

- 표준이라기보다는 **팀 운영 정책과 선호**입니다. 현업에서 주로 쓰이는 패턴은 두 가지입니다:

### A. DAG 파일을 분리 (직관적)
- 장점: 읽기 쉽고 ownership 분리가 명확
- 단점: 공통 코드/설정이 중복될 가능성 → 공통 모듈로 분리 필요

### B. DAG는 분리하되 파일은 1~2개 (Factory 패턴)
- 장점: 공통 구조(prepare → train → eval → register)를 템플릿화하여 유지보수 용이
- 단점: 초심자는 파일 열었을 때 여러 DAG가 생성되는 구조가 낯설 수 있음

- 보통 규모가 작으면 A, 파이프라인 수가 늘어나고 공통 구조가 뚜렷하면 B로 전환하는 경우가 많습니다.

---

## 4가지 케이스별 권장 분리 방식 (현업 감각)

### MNIST (CNN)
- 보통 **별도 DAG** (실험/튜토리얼 성격 시 수동 Trigger 중심)
- MLflow: run 생성 → metrics/artifacts 로깅 → model registry 선택적 사용

### CIFAR-10
- MNIST와 유사한 구조, **별도 DAG** 권장
- 코드/태스크는 공통 템플릿으로 공유(Factory 패턴 적합)

### Tick 데이터 학습
- 업계에서 가장 보수적
- 실시간/준실시간 요구가 강하면 Airflow만으로 처리하지 않는 것이 일반적(스트리밍 또는 피처 스토어 병행)
- Airflow는 주로 배치 롤업(예: 1시간/1일) 또는 데이터 준비 완료 이벤트 기반 트리거 역할로 사용

### 가정집 전력 데이터 (LightGBM)
- 정형 데이터 배치 학습 전형 → Airflow + MLflow 궁합이 좋음
- 스케줄/재처리 성격이 이미지·tick과 다르므로 **별도 DAG** 권장

**결론**: MNIST / CIFAR10 / Tick / Power(LGBM) → 일반적으로 **DAG 4개 권장** (파일은 4개 또는 factory로 1~2개 구성 모두 현업에서 흔함)

---

## 언제 하나의 DAG로 합치기도 하나?

- 네 작업이 **같은 주기**, **같은 큐/리소스 정책**, **같은 재처리 규칙** 및 **동일한 릴리즈 사이클**을 갖고 있고
- 단순히 데이터셋만 바뀌는 동일 파이프라인 형태라면
  - 하나의 DAG + 파라미터 방식으로 dataset을 바꾸는 패턴도 사용됩니다.
- 다만 4가지 작업 성격이 크게 다르면(특히 tick) 이 방식은 권장되지 않습니다.

---

## 옵션별 디렉터리 예시

### 옵션 A: DAG 파일 4개 (직관적)

```text
lakehouse-tick/
└── dags/
    ├── mnist_cnn_train_dag.py
    ├── cifar10_cnn_train_dag.py
    ├── tick_model_train_dag.py
    ├── power_lgbm_train_dag.py
    ├── common/
    │   ├── mlflow_utils.py
    │   ├── data_prep.py
    │   ├── train_tasks.py
    │   └── config.py
    └── scripts/
        ├── train_mnist.py
        ├── train_cifar10.py
        ├── train_tick.py
        └── train_power_lgbm.py
```

### 옵션 B: DAG는 4개지만 파일은 1개 (Factory)

```text
lakehouse-tick/
└── dags/
    ├── model_training_factory_dags.py   # 이 파일 하나에서 dag_id 4개 생성
    ├── configs/
    │   ├── mnist.yaml
    │   ├── cifar10.yaml
    │   ├── tick.yaml
    │   └── power_lgbm.yaml
    ├── common/
    │   ├── mlflow_utils.py
    │   ├── data_prep.py
    │   ├── train_tasks.py
    │   └── config.py
    └── scripts/
        ├── train_image_cnn.py
        ├── train_tick.py
        └── train_power_lgbm.py
```

---

## 다음 단계 제안
원하시면 현재 레포의 `dags/` 구조(이미 존재하는 파일/폴더)에 **최소 변경**으로 맞춰 어떤 옵션(A vs B)이 더 자연스러운지 판단해 드리겠습니다. 또한 원하시면 **4개 DAG 템플릿**(예시 코드)도 생성해 드리겠습니다.
