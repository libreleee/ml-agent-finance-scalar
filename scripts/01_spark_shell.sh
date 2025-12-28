#!/usr/bin/env bash
set -euo pipefail

# Spark/Iceberg/Nessie/MinIO 연결용 예시 스크립트
# 사용자의 Spark 설치 경로/버전에 맞춰 SPARK_HOME을 설정하세요.

: "${SPARK_HOME:?SPARK_HOME is required}"

ICEBERG_VERSION="1.5.2"
SPARK_VERSION_SHORT="3.5"
SCALA_BINARY="2.12"

# 필요한 패키지:
# - iceberg-spark-runtime
# - nessie-spark-extensions (spark3.5)
# - hadoop-aws (s3a)
# - aws-java-sdk-bundle

${SPARK_HOME}/bin/spark-sql   --packages org.apache.iceberg:iceberg-spark-runtime-${SPARK_VERSION_SHORT}_${SCALA_BINARY}:${ICEBERG_VERSION},org.projectnessie.nessie-integrations:nessie-spark-extensions-${SPARK_VERSION_SHORT}_${SCALA_BINARY}:0.96.3,org.apache.hadoop:hadoop-aws:3.3.6,com.amazonaws:aws-java-sdk-bundle:1.12.782,\
com.databricks:spark-xml_${SCALA_BINARY}:0.17.0   --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions,org.projectnessie.spark.extensions.NessieSparkSessionExtensions   --conf spark.sql.catalog.lakehouse=org.apache.iceberg.spark.SparkCatalog   --conf spark.sql.catalog.lakehouse.catalog-impl=org.apache.iceberg.nessie.NessieCatalog   --conf spark.sql.catalog.lakehouse.uri=http://localhost:19120/api/v2   --conf spark.sql.catalog.lakehouse.ref=main   --conf spark.sql.catalog.lakehouse.authentication.type=NONE   --conf spark.sql.catalog.lakehouse.warehouse=s3a://warehouse/   --conf spark.hadoop.fs.s3a.endpoint=http://localhost:9000   --conf spark.hadoop.fs.s3a.access.key=minio   --conf spark.hadoop.fs.s3a.secret.key=minio1234   --conf spark.hadoop.fs.s3a.path.style.access=true   --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false   --conf spark.sql.session.timeZone=UTC
