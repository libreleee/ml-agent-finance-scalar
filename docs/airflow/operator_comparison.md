# Operator 비교: BashOperator, PythonOperator, DockerOperator in Airflow
## 개요
이 문서는 Airflow에서 ML 학습(예: MNIST, PyTorch)을 위한 오퍼레이터(BashOperator, PythonOperator, DockerOperator)를 비교하고, 현업 적용 사례를 요약합니다. (TensorFlow/PyTorch 스크립트 기반, GPU/CUDA 지원 포함.)

## 1. 각 오퍼레이터 개요
### BashOperator
- **용도**: 외부 명령어/스크립트 실행 (예: `python train.py`).
- **장점**: 간단, 외부 도구 통합 용이, 현업 ETL에서 가장 많이 사용.
- **단점**: Python 로직 복잡 시 유지보수 어려움.
- **예시**: `bash_command="python ~/work/ai/ml/mnist-tensorflow/train.py"`.

### PythonOperator
- **용도**: Python 함수 직접 실행 (예: subprocess로 스크립트 호출).
- **장점**: 유연성 높음, 디버깅 용이, ML 로직에 적합.
- **단점**: 외부 명령어 시 subprocess 필요, 현업에서 덜 범용적.
- **예시**: `python_callable=lambda: subprocess.run(["python", "train.py"])`.

### DockerOperator
- **용도**: 컨테이너에서 학습 실행 (예: TensorFlow/PyTorch 이미지).
- **장점**: 의존성 격리, GPU 지원, 운영 확장성 (final_solution 정렬).
- **단점**: 설정 복잡, 컨테이너 시작 느림.
- **예시**: `image="tensorflow/tensorflow:2.15.0-gpu", command=["python", "train.py"]`.

## 2. 비교 표
| 항목          | BashOperator          | PythonOperator       | DockerOperator       |
|---------------|-----------------------|----------------------|----------------------|
| **복잡도**   | 낮음                 | 중간                 | 높음                |
| **의존성 관리**| 없음                 | Python 패키지       | 컨테이너 격리       |
| **GPU 지원** | 제한적 (호스트 의존) | 제한적              | 강력 (device_requests)|
| **현업 사용**| ETL/스크립트 실행    | ML 함수 실행        | 격리 학습/운영     |
| **장점**     | 간단/범용           | 유연/디버깅        | 격리/확장          |
| **단점**     | 로직 제한            | 설치 의존           | 설정 복잡          |

## 3. ML 학습 적용 사례
### MNIST TensorFlow (train.py)
- **BashOperator**: `python train.py` 직접 실행, 로그 Airflow UI에서 확인.
- **PythonOperator**: subprocess로 호출, 에러 핸들링 추가.
- **DockerOperator**: `tensorflow/tensorflow` 컨테이너에서 실행, GPU 지원 (`device_requests`).

### MNIST PyTorch (train_mnist.py)
- argparse 지원, `torch.compile()` 옵션.
- DockerOperator: `pytorch/pytorch` 이미지, CUDA 자동 감지.
- GPU: `torch.cuda.is_available()`로 확인, 로그에 디바이스 정보 출력.

### 전기검침 데이터 (LightGBM)
- DockerOperator로 `python:3.9` + LightGBM 설치, 데이터 마운트.
- MLflow 연동으로 메트릭 로깅.

## 4. 테스트 방법
- **하나의 DAG에 구현**: 두 오퍼레이터 태스크 추가 (병렬 실행).
- **실행**: Airflow 웹 UI에서 트리거, Logs 탭으로 모니터링.
- **비교**: PythonOperator는 빠름, DockerOperator는 안정적.

## 5. 결론 및 추천
- **De facto Standard**: BashOperator (범용), DockerOperator (격리 학습).
- **추천**: 테스트 시 DockerOperator (운영 강함). GPU 필요 시 필수.
- **참고**: final_solution.md 정렬, 수정 없이 스크립트 호출.

(2026년 1월 기준, Airflow 2.x 기반.)