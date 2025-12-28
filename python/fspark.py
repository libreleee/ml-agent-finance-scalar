from pyspark.sql import SparkSession
from datetime import datetime
from pyspark.sql import Row
import os

# SeaweedFS S3 인증 (테스트용)
# NOTE: Using SeaweedFS S3 gateway for testing; keys are set in docker-compose.yml
# Migration Note: Switched from MinIO to SeaweedFS for better small file performance and Iceberg integration.
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', 'seaweedfs_access_key')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'seaweedfs_secret_key')
os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key
os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
os.environ['AWS_REGION'] = 'us-east-1'

s3_endpoint = os.getenv("AWS_ENDPOINT_URL_S3", "http://localhost:8333")
hive_metastore_uri = os.getenv("HIVE_METASTORE_URI", "thrift://localhost:9083")

# Iceberg Warehouse: SeaweedFS S3 gateway
spark = SparkSession.builder \
    .appName("IcebergWindowsConnect") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.hive_prod", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.hive_prod.type", "hive") \
    .config("spark.sql.catalog.hive_prod.uri", hive_metastore_uri) \
    .config("spark.sql.catalog.hive_prod.warehouse", "s3a://lakehouse/warehouse") \
    .config("spark.sql.catalog.hive_prod.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .config("spark.sql.catalog.hive_prod.s3.endpoint", s3_endpoint) \
    .config("spark.sql.catalog.hive_prod.s3.path-style-access", "true") \
    .config("spark.jars.packages", 
            "org.apache.iceberg:iceberg-spark-runtime-4.0_2.13:1.10.0,"
            "org.apache.hadoop:hadoop-aws:3.3.4,"
            "software.amazon.awssdk:bundle:2.25.23,"
            "software.amazon.awssdk:url-connection-client:2.25.23") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    .config("spark.hadoop.fs.s3a.access.key", aws_access_key) \
    .config("spark.hadoop.fs.s3a.secret.key", aws_secret_key) \
    .config("spark.hadoop.fs.s3a.endpoint", s3_endpoint) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.connection.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.socket.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.threads.keepalivetime", "60000") \
    .config("spark.hadoop.fs.s3a.connection.establish.timeout", "60000") \
    .config("spark.hadoop.fs.s3a.multipart.purge.age", "86400") \
    .config("spark.hadoop.hadoop.service.shutdown.timeout", "30000") \
    .config("spark.hadoop.fs.s3a.attempts.maximum", "3") \
    .getOrCreate()

# S3A 설정 추가
spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.connection.timeout", "60000")
spark.sparkContext._jsc.hadoopConfiguration().set("fs.s3a.socket.timeout", "60000")

print("Spark 버전:", spark.version)
print("연결 성공! Spark UI: http://localhost:4040")

# 테스트: 테이블 목록 확인
# spark.sql("SHOW DATABASES IN hive_prod").show()

# 테이블 생성 (Iceberg)
spark.sql("DROP TABLE IF EXISTS hive_prod.option_ticks_db.bronze_option_ticks").show()

spark.sql("""
CREATE TABLE hive_prod.option_ticks_db.bronze_option_ticks (
    timestamp TIMESTAMP,
    symbol STRING,
    bid_price DOUBLE,
    bid_size INT,
    ask_price DOUBLE,
    ask_size INT,
    last_price DOUBLE,
    volume LONG,
    ingest_time TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(timestamp))
""").show()

# 샘플 데이터 적재 (기존 테이블에 append)
sample_rows = [
    Row(timestamp=datetime(2025, 12, 22, 14, 0, 0),
        symbol="ESZ25C5000",
        bid_price=108.0, bid_size=25,
        ask_price=108.5, ask_size=20,
        last_price=108.3, volume=2000,
        ingest_time=datetime.now())
]

from pyspark.sql.types import *
schema = StructType([
    StructField("timestamp", TimestampType(), True),
    StructField("symbol", StringType(), True),
    StructField("bid_price", DoubleType(), True),
    StructField("bid_size", IntegerType(), True),
    StructField("ask_price", DoubleType(), True),
    StructField("ask_size", IntegerType(), True),
    StructField("last_price", DoubleType(), True),
    StructField("volume", LongType(), True),
    StructField("ingest_time", TimestampType(), True)
])

df = spark.createDataFrame(sample_rows, schema)

df.write \
    .mode("append") \
    .insertInto("hive_prod.option_ticks_db.bronze_option_ticks")

print("Windows Python에서 데이터 적재 성공!")

# 확인
spark.sql("SELECT * FROM hive_prod.option_ticks_db.bronze_option_ticks ORDER BY timestamp DESC LIMIT 5").show(truncate=False)

spark.stop()