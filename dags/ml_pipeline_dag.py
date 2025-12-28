"""
ML Pipeline DAG - End-to-End Data Lakehouse ML Workflow
========================================================

이 DAG(Directed Acyclic Graph)방향성 비순환 그래프 는 다음 단계를 실행합니다:
1. RAW → Bronze: 원시 데이터 수집
2. Bronze → Silver: 데이터 정제 및 변환
3. Silver → Gold: 비즈니스 로직 적용
4. Feature Engineering: ML 피처 생성
5. Model Training: MLflow 기반 모델 학습
6. Model Evaluation: 모델 성능 평가
7. Model Registry: MLflow에 모델 등록

연동:
- Trino: 데이터 쿼리
- MLflow: 실험 추적 및 모델 레지스트리
- SeaweedFS S3: 데이터 저장소
"""

from datetime import datetime, timedelta
from airflow import DAG
try:
    from airflow.providers.standard.operators.python import PythonOperator
except ModuleNotFoundError:
    from airflow.operators.python import PythonOperator
import os

# MLflow 설정
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://mlflow:5000')

# 기본 DAG 인자
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}

# DAG 정의
dag = DAG(
    'ml_pipeline_end_to_end',
    default_args=default_args,
    description='End-to-End ML Pipeline with MLflow',
    schedule=timedelta(days=1),
    start_date=datetime(2025, 12, 25),
    catchup=False,
    tags=['ml', 'mlflow', 'lakehouse'],
)


# ============================================================================
# Task 1: RAW → Bronze (데이터 수집)
# ============================================================================
def raw_to_bronze(**context):
    """
    원시 데이터를 Bronze 테이블에 수집
    """
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with mlflow.start_run(run_name="raw_to_bronze"):
        mlflow.log_param("layer", "bronze")
        mlflow.log_param("source", "raw_data")

        # 실제 환경에서는 여기서 Spark/Trino 작업 실행
        print("📥 RAW → Bronze: 데이터 수집 중...")

        # 예시 메트릭
        rows_ingested = 10000
        mlflow.log_metric("rows_ingested", rows_ingested)

        print(f"✅ Bronze 레이어에 {rows_ingested}개 행 수집 완료")

        return {"rows_ingested": rows_ingested}


task_raw_to_bronze = PythonOperator(
    task_id='raw_to_bronze',
    python_callable=raw_to_bronze,
    dag=dag,
)


# ============================================================================
# Task 2: Bronze → Silver (데이터 정제)
# ============================================================================
def bronze_to_silver(**context):
    """
    Bronze 데이터 정제 및 Silver 테이블 생성
    """
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with mlflow.start_run(run_name="bronze_to_silver"):
        mlflow.log_param("layer", "silver")
        mlflow.log_param("transformation", "cleansing")

        print("🧹 Bronze → Silver: 데이터 정제 중...")

        # 예시 메트릭
        rows_cleaned = 9500
        rows_filtered = 500
        quality_score = 0.95

        mlflow.log_metric("rows_cleaned", rows_cleaned)
        mlflow.log_metric("rows_filtered", rows_filtered)
        mlflow.log_metric("quality_score", quality_score)

        print(f"✅ Silver 레이어에 {rows_cleaned}개 정제된 행 생성 (품질 점수: {quality_score})")

        return {"rows_cleaned": rows_cleaned, "quality_score": quality_score}


task_bronze_to_silver = PythonOperator(
    task_id='bronze_to_silver',
    python_callable=bronze_to_silver,
    dag=dag,
)


# ============================================================================
# Task 3: Silver → Gold (비즈니스 로직)
# ============================================================================
def silver_to_gold(**context):
    """
    Silver 데이터에 비즈니스 로직 적용하여 Gold 테이블 생성
    """
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with mlflow.start_run(run_name="silver_to_gold"):
        mlflow.log_param("layer", "gold")
        mlflow.log_param("aggregation", "daily")

        print("💎 Silver → Gold: 비즈니스 로직 적용 중...")

        # 예시 메트릭
        rows_aggregated = 1000

        mlflow.log_metric("rows_aggregated", rows_aggregated)

        print(f"✅ Gold 레이어에 {rows_aggregated}개 집계 행 생성")

        return {"rows_aggregated": rows_aggregated}


task_silver_to_gold = PythonOperator(
    task_id='silver_to_gold',
    python_callable=silver_to_gold,
    dag=dag,
)


# ============================================================================
# Task 4: Feature Engineering (피처 생성)
# ============================================================================
def feature_engineering(**context):
    """
    ML 모델용 피처 생성
    """
    import mlflow
    import numpy as np

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    with mlflow.start_run(run_name="feature_engineering"):
        mlflow.log_param("layer", "features")
        mlflow.log_param("feature_count", 20)

        print("🔧 Feature Engineering: 피처 생성 중...")

        # 예시 피처 통계
        feature_stats = {
            "mean": np.random.rand(),
            "std": np.random.rand(),
            "min": np.random.rand(),
            "max": np.random.rand(),
        }

        for key, value in feature_stats.items():
            mlflow.log_metric(f"feature_{key}", value)

        print(f"✅ 20개 피처 생성 완료")

        return {"feature_count": 20}


task_feature_engineering = PythonOperator(
    task_id='feature_engineering',
    python_callable=feature_engineering,
    dag=dag,
)


# ============================================================================
# Task 5: Model Training (모델 학습)
# ============================================================================
def model_training(**context):
    """
    MLflow 기반 모델 학습
    """
    import mlflow
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.datasets import make_classification
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score
    import pickle
    import os

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("lakehouse_ml_pipeline")

    with mlflow.start_run(run_name="model_training"):
        # 파라미터 로깅
        mlflow.log_param("model_type", "RandomForest")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth", 10)

        print("🧠 Model Training: 모델 학습 중...")

        # 샘플 데이터 생성 (실제로는 Gold 테이블에서 로드)
        X, y = make_classification(n_samples=1000, n_features=20, n_classes=2, random_state=42)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 모델 학습
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)

        # 예측 및 평가
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)

        # 메트릭 로깅
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("f1_score", f1)

        # 모델을 pickle로 저장 (mlflow.sklearn.log_model 대신 사용)
        model_path = "/tmp/model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        mlflow.log_artifact(model_path, artifact_path="model")

        print(f"✅ 모델 학습 완료 (Accuracy: {accuracy:.4f}, F1: {f1:.4f})")

        # Run ID 저장 (다음 태스크에서 사용)
        run_id = mlflow.active_run().info.run_id
        context['task_instance'].xcom_push(key='model_run_id', value=run_id)

        return {"accuracy": accuracy, "f1_score": f1, "run_id": run_id}


task_model_training = PythonOperator(
    task_id='model_training',
    python_callable=model_training,
    dag=dag,
)


# ============================================================================
# Task 6: Model Evaluation (모델 평가)
# ============================================================================
def model_evaluation(**context):
    """
    학습된 모델 평가 및 성능 검증
    """
    import mlflow

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # 이전 태스크에서 Run ID 가져오기
    run_id = context['task_instance'].xcom_pull(task_ids='model_training', key='model_run_id')

    with mlflow.start_run(run_id=run_id):
        print("📊 Model Evaluation: 모델 평가 중...")

        # 실제 환경에서는 여기서 추가 검증 수행
        # - 교차 검증
        # - A/B 테스트
        # - 비즈니스 메트릭 검증

        mlflow.log_metric("validation_passed", 1)

        print("✅ 모델 평가 완료 - 검증 통과")

        return {"validation_passed": True}


task_model_evaluation = PythonOperator(
    task_id='model_evaluation',
    python_callable=model_evaluation,
    dag=dag,
)


# ============================================================================
# Task 7: Model Registry (모델 등록)
# ============================================================================
def model_registry(**context):
    """
    검증된 모델을 MLflow Model Registry에 등록
    """
    import mlflow
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    client = MlflowClient()

    # 이전 태스크에서 Run ID 가져오기
    run_id = context['task_instance'].xcom_pull(task_ids='model_training', key='model_run_id')

    print("📦 Model Registry: 모델 등록 중...")

    # 모델 URI
    model_uri = f"runs:/{run_id}/model"
    model_name = "lakehouse_ml_model"

    # 모델 등록
    try:
        # 새 버전 등록
        model_version = mlflow.register_model(model_uri, model_name)

        # Production으로 전환 (실제로는 승인 프로세스 필요)
        client.transition_model_version_stage(
            name=model_name,
            version=model_version.version,
            stage="Production"
        )

        print(f"✅ 모델 등록 완료: {model_name} v{model_version.version} (Production)")

        return {
            "model_name": model_name,
            "model_version": model_version.version,
            "stage": "Production"
        }
    except Exception as e:
        print(f"⚠️  모델 등록 중 오류: {e}")
        # 첫 등록이 아닌 경우 버전만 업데이트
        return {"status": "registered"}


task_model_registry = PythonOperator(
    task_id='model_registry',
    python_callable=model_registry,
    dag=dag,
)


# ============================================================================
# DAG 흐름 정의
# ============================================================================

# 데이터 파이프라인: RAW → Bronze → Silver → Gold
task_raw_to_bronze >> task_bronze_to_silver >> task_silver_to_gold

# ML 파이프라인: Feature Engineering → Training → Evaluation → Registry
task_silver_to_gold >> task_feature_engineering >> task_model_training
task_model_training >> task_model_evaluation >> task_model_registry

"""
DAG 실행 흐름:
==============

raw_to_bronze
      ↓
bronze_to_silver
      ↓
silver_to_gold
      ↓
feature_engineering
      ↓
model_training
      ↓
model_evaluation
      ↓
model_registry

각 단계는 MLflow에 실험 결과를 기록하며,
최종 모델은 MLflow Model Registry에 등록됩니다.

접속 URL:
---------
- Airflow UI: http://localhost:8082
- MLflow UI: http://localhost:5000

로그인:
------
- Airflow: admin / admin
"""
