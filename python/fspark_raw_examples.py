from pyspark.sql import SparkSession
from datetime import datetime
from pyspark.sql import Row
from pyspark.sql.functions import to_json, struct
from pyspark.sql.utils import AnalysisException
import time
import os
import json
import base64
import ssl
from urllib import request, error

# AWS/SeaweedFS S3 인증 및 엔드포인트 설정 (환경변수 우선)
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', 'seaweedfs_access_key')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'seaweedfs_secret_key')
os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key
os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
os.environ['AWS_REGION'] = 'us-east-1'

s3_endpoint = os.getenv("AWS_ENDPOINT_URL_S3", "http://localhost:8333")
hive_metastore_uri = os.getenv("HIVE_METASTORE_URI", "thrift://localhost:9083")

# CHANGELOG(2025-12-25, start): Iceberg 카탈로그를 Hadoop → Hive로 변경하고 metastore thrift URI를 추가함.
# 이유: Spark가 만든 테이블을 Trino/Superset이 같은 Hive Metastore에서 읽게 하여 시각화 테스트가 바로 되도록 함.
# Spark + Iceberg (기존과 동일한 카탈로그 사용)
spark = SparkSession.builder \
    .appName("IcebergRawExamples") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.hive_prod", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.hive_prod.type", "hive") \
    .config("spark.sql.catalog.hive_prod.uri", hive_metastore_uri) \
    .config("spark.sql.catalog.hive_prod.warehouse", "s3a://lakehouse/warehouse") \
    .config("spark.hadoop.hive.metastore.client.socket.timeout", "300") \
    .config("spark.sql.catalog.hive_prod.lock-impl", "org.apache.iceberg.util.NoopLock") \
    .config("spark.sql.catalog.hive_prod.http-client.type", "urlconnection") \
    .config("spark.sql.catalog.hive_prod.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .config("spark.sql.catalog.hive_prod.s3.endpoint", s3_endpoint) \
    .config("spark.sql.catalog.hive_prod.s3.path-style-access", "true") \
    .config("spark.jars.packages", \
            "org.apache.iceberg:iceberg-spark-runtime-4.0_2.13:1.10.0,org.apache.hadoop:hadoop-aws:3.3.4,software.amazon.awssdk:bundle:2.25.23,software.amazon.awssdk:url-connection-client:2.25.23,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    .config("spark.hadoop.fs.s3a.access.key", aws_access_key) \
    .config("spark.hadoop.fs.s3a.secret.key", aws_secret_key) \
    .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.multipart.copy.enabled", "false") \
    .config("spark.hadoop.fs.s3a.change.detection.mode", "none") \
    .config("spark.hadoop.fs.s3a.fast.upload", "true") \
    .config("spark.hadoop.mapreduce.outputcommitter.factory.scheme.s3a", "org.apache.hadoop.fs.s3a.commit.S3ACommitterFactory") \
    .config("spark.hadoop.fs.s3a.committer.name", "directory") \
    .config("spark.hadoop.fs.s3a.committer.staging.conflict-mode", "replace") \
    .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2") \
    .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.socket.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.threads.keepalivetime", "60000") \
    .config("spark.hadoop.fs.s3a.multipart.purge.age", "86400") \
    .getOrCreate()
# CHANGELOG(2025-12-25, end)

# BUGFIX: Set current catalog to 'hive_prod' to ensure all Spark operations correctly resolve against the Hive Metastore.
spark.catalog.setCurrentCatalog("hive_prod")

print("Spark 버전:", spark.version)

# CHANGELOG(2025-12-27, start): Ensure S3 bucket exists using AWS Java SDK via PySpark
# Reason: To prevent NoSuchBucket exception when writing to a non-existent bucket in a fresh environment.
def ensure_s3_bucket_exists(spark, bucket_name, endpoint, access_key, secret_key):
    try:
        jvm = spark.sparkContext._jvm
        creds = jvm.com.amazonaws.auth.BasicAWSCredentials(access_key, secret_key)
        provider = jvm.com.amazonaws.auth.AWSStaticCredentialsProvider(creds)
        endpoint_config = jvm.com.amazonaws.client.builder.AwsClientBuilder.EndpointConfiguration(
            endpoint, "us-east-1"
        )
        
        s3_client = jvm.com.amazonaws.services.s3.AmazonS3ClientBuilder.standard() \
            .withCredentials(provider) \
            .withEndpointConfiguration(endpoint_config) \
            .withPathStyleAccessEnabled(True) \
            .build()
            
        if not s3_client.doesBucketExistV2(bucket_name):
            s3_client.createBucket(bucket_name)
            print(f"S3 Bucket '{bucket_name}' created successfully.")
        else:
            print(f"S3 Bucket '{bucket_name}' already exists.")
    except Exception as e:
        print(f"Warning: Failed to ensure bucket exists: {e}")

ensure_s3_bucket_exists(spark, "lakehouse", s3_endpoint, aws_access_key, aws_secret_key)
# CHANGELOG(2025-12-27, end)

# ---------------------------------------------------------------------------
# 1) 반정형 예제: JSON 로그를 Raw(파일)로 저장하고, Iceberg 테이블(정형)로 적재
# ---------------------------------------------------------------------------
raw_json_path = "s3a://lakehouse/raw/logs/date={date}/".format(date=datetime.utcnow().strftime('%Y-%m-%d'))

# CHANGELOG(2025-12-25, start): S3A _temporary 파일 충돌 방지용 정리 로직 추가.
# 이유: 이전 실패 실행이 남긴 _temporary 파일 때문에 디렉터리 생성이 실패하는 문제를 회피.
# Clean up leftover _temporary marker from previous failed writes (S3A treats it as a file)
try:
    jconf = spark._jsc.hadoopConfiguration()
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(
        spark._jvm.java.net.URI(raw_json_path),
        jconf,
    )
    temp_path = spark._jvm.org.apache.hadoop.fs.Path(raw_json_path + "_temporary")
    if fs.exists(temp_path):
        fs.delete(temp_path, True)
        print("정리됨: 이전 _temporary 경로 삭제 ->", temp_path)
except Exception as e:
    print("경고: _temporary 정리 실패 ->", e)
# CHANGELOG(2025-12-25, end)

# 샘플 반정형 데이터
sample_logs = [
    {
        "event_time": datetime(2025, 12, 24, 9, 0, 0).isoformat(),
        "level": "INFO",
        "message": "trade executed",
        "meta": json.dumps({"user": "trader01", "order_id": "ord-1001"})
    },

]

# DataFrame 생성 및 raw JSON 파일로 저장 (원본 보존)
df_logs = spark.createDataFrame(sample_logs)
df_logs.write.mode("append").json(raw_json_path)
print("반정형 JSON(raw) 저장 완료 ->", raw_json_path)

# Iceberg 테이블 (bronze layer)로 적재: meta 는 문자열로 보관 (schema-on-read로 파싱 가능)
spark.sql("CREATE DATABASE IF NOT EXISTS hive_prod.logs_db")

# 동시성 문제 방지를 위해 테이블 존재 여부 확인 후 생성
table_name = "hive_prod.logs_db.raw_logs_v3"
if not spark.catalog.tableExists(table_name):
    spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        event_time TIMESTAMP,
        level STRING,
        message STRING,
        meta STRING,
        ingest_time TIMESTAMP
    )
    USING iceberg
    PARTITIONED BY (days(event_time))
    """)
    print(f"테이블 {table_name} 생성 완료")
else:
    print(f"테이블 {table_name} 이미 존재함 (생성 건너뜀)")

# meta 컬럼은 이미 JSON 문자열이므로 그대로 사용하고 timestamp와 ingest_time 컬럼 추가
from pyspark.sql.functions import current_timestamp

df_logs_for_table = df_logs.withColumn("event_time", df_logs.event_time.cast("timestamp")).withColumn("ingest_time", current_timestamp())

# 데이터를 추가 모드로 삽입 (테이블이 존재하지 않으면 에러 대신 생성)
try:
    df_logs_for_table.write.mode("append").insertInto(table_name)
    print(f"반정형 데이터 -> Iceberg 테이블({table_name})로 적재 완료")
except AnalysisException as e:
    if "TABLE_OR_VIEW_NOT_FOUND" in str(e):
        # 테이블이 없으면 overwrite 모드로 생성
        print(f"테이블 {table_name}을(를) 찾을 수 없어 새로 생성합니다.")
        df_logs_for_table.write.mode("overwrite").saveAsTable(table_name)
        print(f"테이블을 새로 생성하고 데이터 적재 완료: {table_name}")
    else:
        # 테이블 생성 경쟁에서 졌을 경우, 잠깐 기다렸다가 다시 시도
        print("데이터 적재 중 분석 오류 발생, 2초 후 재시도합니다.", e)
        time.sleep(2)
        df_logs_for_table.write.mode("append").insertInto(table_name)
        print(f"데이터 재시도 적재 완료: {table_name}")

# ---------------------------------------------------------------------------
# 2) 비정형 예제: 이미지(비트스트림)를 Raw 경로(S3)로 저장 (파일 단위 보관)
# ---------------------------------------------------------------------------
# 샘플 바이너리(예시용 텍스트를 바이너리로 저장)
sample_bytes = b"This is a sample binary content representing an image or other file."
image_s3_path = "s3a://lakehouse/raw/images/{date}/sample.txt".format(date=datetime.utcnow().strftime('%Y-%m-%d'))
image_local_path = "./data/image1.png"

# Hadoop FileSystem을 사용해 S3에 바이너리 파일을 직접 작성
jconf = spark._jsc.hadoopConfiguration()
fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(spark._jvm.java.net.URI(image_s3_path), jconf)
path = spark._jvm.org.apache.hadoop.fs.Path(image_s3_path)

try:
    out = fs.create(path, True)
    out.write(bytearray(sample_bytes))
    out.close()
    print("비정형(바이너리) 파일 저장 완료 ->", image_s3_path)
except Exception as e:
    print("비정형 저장 실패:", e)

# 로컬 바이너리 파일을 읽어서 동일한 날짜 하위에 업로드
if os.path.isfile(image_local_path):
    local_target_path = "s3a://lakehouse/raw/images/{date}/image1.png".format(date=datetime.utcnow().strftime('%Y-%m-%d'))
    local_path_obj = spark._jvm.org.apache.hadoop.fs.Path(local_target_path)
    try:
        out = fs.create(local_path_obj, True)
        with open(image_local_path, 'rb') as src:
            out.write(bytearray(src.read()))
        out.close()
        print("로컬 이미지 파일 업로드 완료 ->", local_target_path)
    except Exception as e:
        print("로컬 이미지 업로드 실패:", e)
else:
    print("로컬 이미지 파일이 없음 ->", image_local_path)

# 확인(간단히 목록 확인)
try:
    files = fs.listStatus(spark._jvm.org.apache.hadoop.fs.Path("s3a://lakehouse/raw/"))
    print("raw/ 경로에 있는 항목 수:", len(files))
except Exception as e:
    print("raw/ 경로 조회 실패:", e)

print("예제 스크립트 완료")

# CHANGELOG(2025-12-28, start): Add Iceberg table for Image Metadata
# Reason: Streamlit Gallery app requires 'media_db.image_metadata' table.
spark.sql("CREATE DATABASE IF NOT EXISTS hive_prod.media_db")

if not spark.catalog.tableExists("hive_prod.media_db.image_metadata"):
    spark.sql("""
    CREATE TABLE hive_prod.media_db.image_metadata (
        image_id STRING,
        s3_path STRING,
        file_size LONG,
        mime_type STRING,
        upload_time TIMESTAMP,
        source_system STRING,
        tag STRING
    )
    USING iceberg
    """)
    print("테이블 hive_prod.media_db.image_metadata 생성 완료")

# Prepare metadata for Iceberg
image_meta_rows = [
    {
        "image_id": "sample-txt",
        "s3_path": image_s3_path,
        "file_size": len(sample_bytes),
        "mime_type": "text/plain",
        "upload_time": datetime.utcnow(),
        "source_system": "batch",
        "tag": "analytics",
    }
]
if os.path.isfile(image_local_path):
    local_target_path = "s3a://lakehouse/raw/images/{date}/image1.png".format(date=datetime.utcnow().strftime('%Y-%m-%d'))
    image_meta_rows.append({
        "image_id": "image1",
        "s3_path": local_target_path,
        "file_size": os.path.getsize(image_local_path),
        "mime_type": "image/png",
        "upload_time": datetime.utcnow(),
        "source_system": "manual",
        "tag": "product",
    })

df_images = spark.createDataFrame(image_meta_rows)
# 테이블 스키마 순서에 맞춰 컬럼 정렬 (insertInto는 위치 기반 매핑)
df_images = df_images.select("image_id", "s3_path", "file_size", "mime_type", "upload_time", "source_system", "tag")
df_images.write.mode("append").insertInto("hive_prod.media_db.image_metadata")
print("이미지 메타데이터 -> Iceberg 테이블(media_db.image_metadata) 적재 완료")
# CHANGELOG(2025-12-28, end)

# CHANGELOG(2025-12-25, start): OpenSearch에 예제 데이터를 색인하도록 추가.
# 이유: Dashboards에서 샘플이 아닌 우리 데이터도 바로 조회/시각화할 수 있게 함.
def opensearch_request(method, path, payload=None):
    base_url = os.getenv("OPENSEARCH_URL", "https://localhost:9200").rstrip("/")
    url = f"{base_url}{path}"
    username = os.getenv("OPENSEARCH_USERNAME", "admin")
    password = os.getenv("OPENSEARCH_PASSWORD", "Admin@123")
    auth = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    data = None
    headers = {"Authorization": f"Basic {auth}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=data, method=method, headers=headers)
    context = ssl._create_unverified_context()
    with request.urlopen(req, context=context, timeout=10) as resp:
        return resp.read().decode("utf-8")


def index_doc(index_name, doc_id, doc):
    opensearch_request("PUT", f"/{index_name}/_doc/{doc_id}", doc)


try:
    # 로그 데이터 색인
    for item in sample_logs:
        meta_value = item.get("meta")
        try:
            meta_value = json.loads(meta_value) if meta_value else None
        except json.JSONDecodeError:
            pass
        doc = {
            "event_time": item.get("event_time"),
            "level": item.get("level"),
            "message": item.get("message"),
            "meta": meta_value,
            "ingest_time": datetime.utcnow().isoformat(),
        }
        doc_id = f"log-{item.get('event_time')}-{item.get('level')}"
        index_doc("lakehouse_raw_logs", doc_id, doc)

    # 이미지 메타데이터 색인
    image_docs = [
        {
            "image_id": "sample-txt",
            "s3_path": image_s3_path,
            "file_size": len(sample_bytes),
            "mime_type": "text/plain",
            "upload_time": datetime.utcnow().isoformat(),
            "source_system": "batch",
            "tag": "analytics",
        }
    ]
    if os.path.isfile(image_local_path):
        image_docs.append(
            {
                "image_id": "image1",
                "s3_path": local_target_path,
                "file_size": os.path.getsize(image_local_path),
                "mime_type": "image/png",
                "upload_time": datetime.utcnow().isoformat(),
                "source_system": "manual",
                "tag": "product",
            }
        )

    for doc in image_docs:
        doc_id = f"img-{doc['image_id']}"
        index_doc("lakehouse_image_metadata", doc_id, doc)

    print("OpenSearch 색인 완료 -> lakehouse_raw_logs, lakehouse_image_metadata")
except error.URLError as e:
    print("OpenSearch 색인 실패:", e)
# CHANGELOG(2025-12-25, end)

spark.stop()
