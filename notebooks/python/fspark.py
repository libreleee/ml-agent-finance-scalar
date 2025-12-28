from pyspark.sql import SparkSession
from datetime import datetime
from pyspark.sql import Row
import os

# SeaweedFS S3 인증 (테스트용)
# NOTE: Using SeaweedFS S3 gateway for testing; keys are set in docker-compose.yml
os.environ['AWS_ACCESS_KEY_ID'] = 'seaweedfs_access_key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'seaweedfs_secret_key'
os.environ['AWS_REGION'] = 'us-east-1'  # 무시됨 but 필요

spark = SparkSession.builder \
    .appName("IcebergWindowsConnect") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.hive_prod", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.hive_prod.type", "hive") \
    .config("spark.sql.catalog.hive_prod.uri", "thrift://localhost:9083") \
    .config("spark.sql.catalog.hive_prod.warehouse", "s3a://lakehouse/warehouse/") \
    .config("spark.sql.catalog.hive_prod.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .config("spark.sql.catalog.hive_prod.s3.endpoint", "http://seaweedfs-s3:8333") \
    .config("spark.sql.catalog.hive_prod.s3.path-style-access", "true") \
    .config("spark.jars.packages", 
            "org.apache.iceberg:iceberg-spark-runtime-4.0_2.13:1.10.0,"  # Spark 4.0 + Scala 2.13 build (available on Maven Central)
            "software.amazon.awssdk:bundle:2.25.23,"
            "software.amazon.awssdk:url-connection-client:2.25.23") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    .config("spark.hadoop.fs.s3a.access.key", "seaweedfs_access_key") \
    .config("spark.hadoop.fs.s3a.secret.key", "seaweedfs_secret_key") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://ceph-rgw:8000") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .getOrCreate()

print("Spark 버전:", spark.version)
print("연결 성공! Spark UI: http://localhost:4040 (또는 4041)")

# 테스트: 테이블 목록 확인
spark.sql("SHOW DATABASES IN hive_prod").show()

'''

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

df.writeTo("hive_prod.option_ticks_db.bronze_option_ticks") \
    .using("iceberg") \
    .partitionedBy("days(timestamp)") \
    .option("format", "parquet") \
    .mode("append") \
    .save()

print("Windows Python에서 데이터 적재 성공!")

# 확인
spark.sql("SELECT * FROM hive_prod.option_ticks_db.bronze_option_ticks ORDER BY timestamp DESC LIMIT 5").show(truncate=False)

spark.stop()
'''