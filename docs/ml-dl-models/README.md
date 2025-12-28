# ML/DL 모델 통합 문서

## 📋 개요

현재 lakehouse-tick 프로젝트에 **XGBoost**, **LightGBM**, **TensorFlow/Keras**, **PyTorch** 기반 모델을 통합하기 위한 가능성 분석 및 구현 가이드입니다.

**최종 답변**: ✅ **모든 모델을 동작시킬 수 있습니다!**

## 🎯 핵심 결론

| 모델 | 가능 여부 | 난이도 | 리소스 증가 | 우선순위 |
|------|----------|-------|------------|---------|
| **XGBoost** | ✅ | ⭐ 쉬움 | 불필요 | 1 (가장 높음) |
| **LightGBM** | ✅ | ⭐ 쉬움 | 불필요 | 2 |
| **TF MNIST MLP** | ✅ | ⭐⭐ 중간 | 메모리 2→4GB | 3 |
| **TF MNIST CNN** | ✅ | ⭐⭐ 중간 | 메모리 2→6GB, CPU 2→4 | 4 |
| **PyTorch MLP** | ✅ | ⭐⭐ 중간 | 메모리 2→4GB | 5 |
| **PyTorch CNN** | ✅ | ⭐⭐ 중간 | 메모리 2→6GB, CPU 2→4 | 6 |

## 📚 문서 구조

### [1️⃣ 가능성 분석 (01-FEASIBILITY_ANALYSIS.md)](01-FEASIBILITY_ANALYSIS.md)
**대상**: 각 모델이 정말 가능한지 알고 싶은 분들

**주요 내용**:
- 현재 인프라 상태 분석 (Airflow 2.8.0, MLflow 2.9.2, scikit-learn 1.3.2)
- 모델별 가능성 평가 (XGBoost, LightGBM, TensorFlow, PyTorch)
- 필요한 리소스 요구사항 (CPU, Memory, Disk)
- 제약사항 및 고려사항
- 예상 성능 (학습 시간, 정확도, 메모리 사용량)

**읽으면 답할 수 있는 질문**:
- ❓ XGBoost를 지금 바로 사용할 수 있나?
- ❓ 딥러닝 모델에는 추가 리소스가 필요한가?
- ❓ 각 모델의 학습 시간은 얼마나 소요되나?

---

### [2️⃣ 구현 가이드 (02-IMPLEMENTATION_GUIDE.md)](02-IMPLEMENTATION_GUIDE.md)
**대상**: 실제 구현 절차를 단계별로 알고 싶은 분들

**주요 내용**:
- 1단계: 의존성 추가 (requirements-airflow.txt 수정)
- 2단계: Docker 설정 변경 (docker-compose-mlops.yml 수정)
- 3단계: Airflow DAG 작성 (패턴 및 스켈레톤)
- 4단계: MLflow 통합 (autologging 설정)
- 5단계: 테스트 및 검증
- 트러블슈팅 (자주 마주치는 문제들)

**읽으면 답할 수 있는 질문**:
- ❓ requirements-airflow.txt에 어떤 라이브러리를 추가해야 하나?
- ❓ Docker의 CPU/메모리 제한은 어떻게 증가시키나?
- ❓ DAG 파일을 어디에 생성해야 하나?

---

### [3️⃣ 모델 사양 (03-MODEL_SPECIFICATIONS.md)](03-MODEL_SPECIFICATIONS.md)
**대상**: 각 모델의 상세 스펙과 하이퍼파라미터를 알고 싶은 분들

**주요 내용**:
- **XGBoost**: 파라미터 (max_depth, eta, objective), 모델 구조, 예상 성능
- **LightGBM**: 파라미터 (num_leaves, learning_rate), 모델 구조, 예상 성능
- **TensorFlow/Keras**:
  - MNIST MLP 아키텍처 (Flatten → Dense(128) → Dropout → Dense(10))
  - MNIST CNN 아키텍처 (Conv2D → MaxPool → Flatten → Dense)
  - 예상 성능 (MLP: 97%, CNN: 99% 정확도)
- **PyTorch**:
  - MLP class 구현 (nn.Module 상속)
  - CNN class 구현 (Conv2d, Linear layers)

**읽으면 답할 수 있는 질문**:
- ❓ XGBoost의 max_depth는 몇으로 설정하면 좋을까?
- ❓ MNIST MLP와 CNN의 차이는 뭔가?
- ❓ 각 모델의 파라미터 수는 몇 개인가?

---

### [4️⃣ Airflow DAG 예제 (04-AIRFLOW_DAG_EXAMPLES.md)](04-AIRFLOW_DAG_EXAMPLES.md)
**대상**: 실제 DAG 코드를 보고 싶은 분들

**주요 내용**:
- **XGBoost DAG**:
  - load_data() → train_xgboost() → register_model()
  - xgb.DMatrix 생성, mlflow.xgboost.autolog() 사용
  - MLflow 모델 레지스트리에 자동 등록

- **LightGBM DAG**:
  - XGBoost와 유사한 구조
  - lgb.Dataset 생성, mlflow.lightgbm.autolog() 사용

- **TensorFlow MNIST DAG**:
  - download_mnist() → train_mlp()/train_cnn() → register_model()
  - tf.keras.Sequential 모델 정의
  - mlflow.tensorflow.autolog() 사용

- **PyTorch MNIST DAG**:
  - MLP/CNN class 정의
  - DataLoader 사용, 수동 학습 루프
  - mlflow.pytorch.autolog() 사용

**읽으면 답할 수 있는 질문**:
- ❓ XGBoost DAG는 정확히 어떻게 구성되나?
- ❓ MLflow autologging을 어떻게 사용하나?
- ❓ PyTorch의 학습 루프는 어떻게 작성하나?

---

### [5️⃣ 실행 계획 (05-EXECUTION_PLAN.md)](05-EXECUTION_PLAN.md)
**대상**: 단계별 실행 계획과 체크리스트를 보고 싶은 분들

**주요 내용**:
- **Phase 1** (1-2시간): 사전 준비 (환경 확인, 백업)
- **Phase 2** (20-30분): Docker 이미지 재빌드
- **Phase 3** (1-2시간): Traditional ML DAG 구현 (XGBoost, LightGBM)
- **Phase 4** (2-3시간): Deep Learning DAG 구현 (TensorFlow, PyTorch)
- **Phase 5**: 최적화 및 모니터링

**각 단계별**:
- ✅ 체크리스트 (할 일 목록)
- 🧪 테스트 케이스
- 🔄 롤백 전략 (문제 발생 시)
- 📊 모니터링 방법 (Airflow UI, MLflow UI, 로그)

**읽으면 답할 수 있는 질문**:
- ❓ 먼저 어느 모델부터 구현해야 하나?
- ❓ 각 단계에서 해야 할 일이 무엇인가?
- ❓ 문제가 발생했을 때 어떻게 롤백하나?

---

## 🚀 빠른 시작 (Quick Start)

### 5분 안에 상황 파악하기
1. 이 README 읽기 ✓
2. [01-FEASIBILITY_ANALYSIS.md](01-FEASIBILITY_ANALYSIS.md)의 "결론" 섹션 읽기
3. **결론**: 모든 모델 가능! 단, DL 모델은 Docker 리소스 증가 필요

### 30분 안에 구현 방법 이해하기
1. [02-IMPLEMENTATION_GUIDE.md](02-IMPLEMENTATION_GUIDE.md) - "사전 준비" ~ "2단계" 읽기
2. [05-EXECUTION_PLAN.md](05-EXECUTION_PLAN.md) - "Phase 1, 2" 읽기
3. 이해: Docker 설정 변경 + 의존성 추가 필요

### 실제 구현 전 전체 이해하기
1. [01-FEASIBILITY_ANALYSIS.md](01-FEASIBILITY_ANALYSIS.md) - 전체 읽기
2. [02-IMPLEMENTATION_GUIDE.md](02-IMPLEMENTATION_GUIDE.md) - 전체 읽기
3. [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md) - 필요한 부분 읽기

---

## 📊 모델별 리소스 요구사항

### 현재 상태
```yaml
airflow-worker:
  CPU: 2 cores
  Memory: 2GB
```

### 권장 변경
```yaml
airflow-worker:
  CPU: 6 cores      # 2 → 6 (권장)
  Memory: 8GB       # 2GB → 8GB (권장)
```

**참고**: XGBoost/LightGBM은 현재 리소스로도 가능합니다!

---

## 🔗 관련 파일

### 기존 ML 파이프라인 참고
- 위치: `/home/i/work/ai/lakehouse-tick/dags/ml_pipeline_dag.py`
- 내용: scikit-learn RandomForestClassifier DAG 패턴

### 수정이 필요한 파일
- `/home/i/work/ai/lakehouse-tick/requirements-airflow.txt` - 의존성 추가
- `/home/i/work/ai/lakehouse-tick/docker-compose-mlops.yml` - 리소스 증가

### 생성할 DAG 파일들
- `dags/xgboost_pipeline_dag.py` - XGBoost 분류
- `dags/lightgbm_pipeline_dag.py` - LightGBM 분류
- `dags/tensorflow_mnist_mlp_dag.py` - TensorFlow MNIST MLP
- `dags/tensorflow_mnist_cnn_dag.py` - TensorFlow MNIST CNN
- `dags/pytorch_mnist_mlp_dag.py` - PyTorch MNIST MLP
- `dags/pytorch_mnist_cnn_dag.py` - PyTorch MNIST CNN

---

## ✅ 성공 기준

모든 DAG가 다음을 만족하면 성공:

1. **DAG 실행**
   - [ ] Airflow UI에서 DAG 인식됨
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

## 📞 문서 사용 팁

| 상황 | 읽을 문서 |
|------|----------|
| "정말 가능한가?" 물어볼 때 | [01-FEASIBILITY_ANALYSIS.md](01-FEASIBILITY_ANALYSIS.md) |
| "어떻게 시작하지?" 모를 때 | [02-IMPLEMENTATION_GUIDE.md](02-IMPLEMENTATION_GUIDE.md) |
| "XGBoost의 max_depth는 몇?" 물어볼 때 | [03-MODEL_SPECIFICATIONS.md](03-MODEL_SPECIFICATIONS.md) |
| "DAG 코드가 뭐야?" 궁금할 때 | [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md) |
| "단계별로 뭘 하면 돼?" 물어볼 때 | [05-EXECUTION_PLAN.md](05-EXECUTION_PLAN.md) |
| "뭐부터 시작해?" 모를 때 | 우선순위: XGBoost → LightGBM → TF MLP → TF CNN → PyTorch MLP → PyTorch CNN |

---

## 🎓 학습 경로

### 초급자 (ML 경험 없음)
1. README 읽기 ✓
2. [01-FEASIBILITY_ANALYSIS.md](01-FEASIBILITY_ANALYSIS.md) - "결론" 섹션
3. [03-MODEL_SPECIFICATIONS.md](03-MODEL_SPECIFICATIONS.md) - "성능 비교" 섹션

### 중급자 (ML 경험 있음, 실제 구현은 처음)
1. [01-FEASIBILITY_ANALYSIS.md](01-FEASIBILITY_ANALYSIS.md) - 전체
2. [02-IMPLEMENTATION_GUIDE.md](02-IMPLEMENTATION_GUIDE.md) - 전체
3. [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md) - 필요 부분

### 고급자 (Airflow/MLflow 경험 있음)
1. [03-MODEL_SPECIFICATIONS.md](03-MODEL_SPECIFICATIONS.md) - 하이퍼파라미터
2. [04-AIRFLOW_DAG_EXAMPLES.md](04-AIRFLOW_DAG_EXAMPLES.md) - 코드 예제
3. [05-EXECUTION_PLAN.md](05-EXECUTION_PLAN.md) - 체크리스트

---

## 🔄 다음 단계

이 문서를 읽은 후:

1. ✅ **이해 완료** → [02-IMPLEMENTATION_GUIDE.md](02-IMPLEMENTATION_GUIDE.md)로 이동하여 구현 준비
2. ❓ **더 알고 싶음** → 관련 섹션 다시 읽기
3. 🚀 **바로 시작** → 우선순위 1번 (XGBoost)부터 시작

---

**작성일**: 2025-12-27
**프로젝트**: lakehouse-tick ML/DL 모델 통합
**상태**: 📋 문서 완성 (구현 전)
