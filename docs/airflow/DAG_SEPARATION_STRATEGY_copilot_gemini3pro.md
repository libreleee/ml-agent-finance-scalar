# DAG 분리 전략

각 도메인(예: 이미지, 금융, 전력)과 목적, 모델링 방식(CNN, LightGBM 등)이 서로 다르므로, 각 파이프라인을 **별도의 DAG 파일로 분리**하는 것을 권장합니다.

아래는 그 이유와 권장 파일 구조입니다.

---

## 이유

### 1) 독립적인 스케줄링 (Scheduling)
- 각 작업은 데이터 생성 주기나 학습 시점이 다를 수 있습니다.
  - **Tick Data**: 장 마감 후 매일 또는 실시간에 가깝게 학습할 수 있음.
  - **가정집 전력 데이터**: 월별 청구 또는 일별 집계 후 실행.
  - **MNIST / CIFAR-10**: 실험적 성격으로 필요 시 수동 Trigger 또는 모델 변경 시만 실행.
- **결론**: 하나의 DAG에 묶으면 서로 다른 주기를 맞추기 위해 불필요한 분기(Branch)를 추가해야 하며, 원치 않는 시점에 작업이 실행될 수 있습니다.

### 2) 리소스 격리 및 의존성 관리 (Resource & Dependencies)
- **MNIST/CIFAR-10 (CNN)**: GPU 필요, TensorFlow/PyTorch 등 무거운 라이브러리 사용.
- **전력 데이터 (LightGBM)**: CPU 중심, 다른 메모리 사용 패턴.
- **결론**: DAG 분리로 Airflow의 Queue/Pool 기능을 활용해 자원별로 워커를 할당하거나, 한 작업의 실패가 다른 파이프라인에 영향을 주지 않게 할 수 있습니다.

### 3) 유지보수와 가독성 (Maintainability)
- 하나의 파일에 여러 로직을 넣으면 코드가 길어지고 실수로 다른 파이프라인을 건드릴 위험이 커집니다.
- 분리하면 각 도메인별로 코드 확인과 변경이 쉬워집니다.

### 4) 실패 격리 (Failure Isolation)
- 예: Tick Data 수집 서버 다운으로 DAG가 실패했을 때 전체가 'Failed' 상태가 되면 다른 파이프라인의 상태 확인이나 재시도가 번거로워질 수 있습니다.
- 분리하면 해당 DAG만 실패하고 나머지는 정상적으로 운영됩니다.

---

## 추천 파일 구조

```text
dags/
├── vision/
│   ├── mnist_cnn_dag.py        # MNIST CNN 학습
│   └── cifar10_model_dag.py    # CIFAR-10 모델 학습
├── finance/
│   └── tick_data_pipeline.py   # Tick Data 학습
├── energy/
│   └── power_usage_lgbm.py     # 전력 데이터 LightGBM 학습
└── utils/
    ├── s3_utils.py
    └── slack_alert.py
```

> 참고: Airflow 설정에 따라 하위 폴더 스캔(scanning)이 켜져 있어야 폴더별 정리가 가능합니다. 설정이 없다면 `dags/` 바로 아래에 prefix를 붙여 구분하세요.

---

## 요약
각 파이프라인을 별도의 DAG로 분리하여 관리하는 것을 권장합니다. 확장성·유지보수·운영 안정성 면에서 유리합니다.

설명이 충분하다면, 요청하신 4가지 케이스에 대한 DAG 템플릿 생성을 도와드릴까요?
