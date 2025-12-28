# DAG Separation Strategy (Copilot — Raptor)

## 요약 ✅
**목표**: ML(예: LightGBM)과 DL(예: CNN)을 포함한 여러 유형의 학습 작업을 안정적이고 유지보수 가능한 방식으로 Airflow에 배치하기 위한 권장 전략을 정리합니다.

- **한 파일로 가능**: 파라미터화된 단일 DAG으로 ML/DL 모두 처리 가능
- **권장 아키텍처**: "파라미터화된 템플릿 DAG + 모델별 래퍼" 또는 "템플릿 DAG 하나" 방식

---

## 1. 주요 옵션 및 장단점 ⚖️

### A. 모델별로 각각의 DAG
- 장점: 간단하고 분리 규칙 명확, 개별 스케줄·권한 설정 쉬움
- 단점: 코드 중복, 유지보수 비용 증가

### B. 파라미터화된 단일 DAG (권장)
- 장점: 코드 재사용성 증가, 공통 로직(데이터 준비·로깅·레지스트리) 일원화
- 단점: 분기 로직/테스트 복잡도 증가

### C. 템플릿 + 경량 래퍼
- `train_template.py`(공통 로직) + `train_mnist.py`, `train_lightgbm.py`(conf 전달)
- 장점: 템플릿 재사용 + 모델별 스케줄 독립성

---

## 2. 설계 패턴 및 구현 권장사항 🔧

### 공통 설계 요소
- 공통 Task: 데이터 준비 → 학습 → 평가 → 레지스트리(MLflow)
- 학습 Task는 `model_type`으로 분기하여 적절한 trainer 호출
- 설정 전달: `dag_run.conf` 또는 Airflow `Variable`/`Connection`

### 모델별 분기 예시
```python
conf = context['dag_run'].conf or {}
model_type = conf.get('model_type','lightgbm')
if model_type == 'cnn':
    run_cnn(conf)
else:
    run_lightgbm(conf)
```

### 모듈화
- `python/ml/trainers.py`: 모델별 데이터 로드·전처리·학습·평가 함수 집약
- `configs/*.yaml`: 하이퍼파라미터, 리소스 요구(GPU/CPU), 스케줄 정의

---

## 3. 리소스·운영 고려사항 ⚠️

- GPU 필요(CNN): `KubernetesPodOperator`나 GPU-enabled worker 사용 권장
- 의존성 분리: 모델별 Docker 이미지(심지어 base 이미지 분리 권장)
- 동시성·큐: Airflow `pools`/`queues`/`task_concurrency`로 GPU/CPU 작업 격리
- 시크릿/접속정보: Airflow Connections / Secret backends 사용
- 모니터링: MLflow 실험명을 모델별로 구분(예: `mnist_cnn`, `household_lgbm`)

---

## 4. MLflow & Model Registry 운영 팁 📦
- 실험 네이밍 규칙: `{dataset}_{model}_{profile}` (예: `mnist_cnn_v1`)
- 모델 네이밍: 명시적이고 중복 없는 이름 (예: `household_power_lgbm`)
- 레지스트리 단계 전환: 자동화를 하되 승인 프로세스(검증) 고려

---

## 5. 체크리스트 (배포 전) ✔️
- [ ] 모델별 이미지와 의존성 목록 작성
- [ ] GPU 작업은 별도 queue/pool로 분리
- [ ] MLflow 서버 접근 권한/URI 확인 (`MLFLOW_TRACKING_URI`)
- [ ] `trainers` 모듈로 기능 분리 및 단위 테스트 작성
- [ ] 작은 데이터로 end-to-end dry-run

---

## 6. 예시 디렉토리 구조 제안
```
dags/
  train_template.py
  train_mnist.py  # optional wrapper
  train_lightgbm.py
python/
  ml/
    trainers.py
configs/
  mnist.yaml
  cifar10.yaml
  tick_forecast.yaml
```

---

## 7. 권장 기본 선택지
- 빠른 시작: **파라미터화된 템플릿 DAG** + `trainers` 모듈(모델별 func dispatch)
- 운영 확장: 모델별 Docker 이미지 + Kubernetes 기반 실행으로 리소스 격리

---

## 8. 다음 단계 제안 💡
- 원하는 경우: (A) 샘플 `train_template.py` 생성, 또는 (B) MNIST CNN 샘플 DAG 생성
- 어떤 예제를 먼저 만들까요? (선택: `mnist_cnn`, `cifar10`, `tick_forecasting`, `household_power_lgbm`)

---

*문서 생성: Copilot (Raptor mini — Preview)*
