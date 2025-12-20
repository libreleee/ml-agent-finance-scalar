from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from pyspark.sql import functions as F, types as T

from spark_jobs.common_spark import build_spark


TICK_SCHEMA = T.StructType([
    T.StructField("ymcode", T.StringType(), True),
    T.StructField("code", T.StringType(), True),
    T.StructField("strike", T.IntegerType(), True),
    T.StructField("idate", T.IntegerType(), True),
    T.StructField("itime", T.IntegerType(), True),
    T.StructField("tdate", T.TimestampType(), True),
    T.StructField("tcnt", T.LongType(), True),
    T.StructField("c", T.DoubleType(), True),
    T.StructField("o", T.DoubleType(), True),
    T.StructField("h", T.DoubleType(), True),
    T.StructField("l", T.DoubleType(), True),
    T.StructField("oi", T.DoubleType(), True),
    T.StructField("ccnt", T.LongType(), True),
])

CODE_SCHEMA = T.StructType([
    T.StructField("ymcode", T.StringType(), True),
    T.StructField("code", T.StringType(), True),
    T.StructField("lastday", T.IntegerType(), True),
])


def detect_row_tag(xml_path: str) -> str:
    root = ET.parse(xml_path).getroot()
    # first child tag is the row tag (dataset element)
    return list(root)[0].tag


def read_xml_rows(spark, xml_path: str, row_tag: str, schema: T.StructType):
    # Requires spark-xml package in your Spark runtime:
    # com.databricks:spark-xml_2.12:0.17.0 (or compatible)
    #
    # If spark-xml is not available in your environment, convert XML to JSON/Parquet via Python first.
    return (
        spark.read.format("xml")
        .option("rowTag", row_tag)
        .schema(schema)
        .load(xml_path)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-call", required=True)
    ap.add_argument("--tick-put", required=True)
    ap.add_argument("--code-call", required=True)
    ap.add_argument("--code-put", required=True)
    args = ap.parse_args()

    spark = build_spark("ingest_xml_to_bronze")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.options")

    ingest_ts = datetime.now(timezone.utc).isoformat()

    # Tick CALL
    tick_call_tag = detect_row_tag(args.tick_call)
    df_tc = read_xml_rows(spark, args.tick_call, tick_call_tag, TICK_SCHEMA) \
        .withColumn("src_file", F.lit(os.path.basename(args.tick_call))) \
        .withColumn("side", F.lit("CALL")) \
        .withColumn("ingest_ts", F.to_timestamp(F.lit(ingest_ts)))

    # Tick PUT
    tick_put_tag = detect_row_tag(args.tick_put)
    df_tp = read_xml_rows(spark, args.tick_put, tick_put_tag, TICK_SCHEMA) \
        .withColumn("src_file", F.lit(os.path.basename(args.tick_put))) \
        .withColumn("side", F.lit("PUT")) \
        .withColumn("ingest_ts", F.to_timestamp(F.lit(ingest_ts)))

    # Code CALL
    code_call_tag = detect_row_tag(args.code_call)
    df_cc = read_xml_rows(spark, args.code_call, code_call_tag, CODE_SCHEMA) \
        .withColumn("src_file", F.lit(os.path.basename(args.code_call))) \
        .withColumn("side", F.lit("CALL")) \
        .withColumn("ingest_ts", F.to_timestamp(F.lit(ingest_ts)))

    # Code PUT
    code_put_tag = detect_row_tag(args.code_put)
    df_cp = read_xml_rows(spark, args.code_put, code_put_tag, CODE_SCHEMA) \
        .withColumn("src_file", F.lit(os.path.basename(args.code_put))) \
        .withColumn("side", F.lit("PUT")) \
        .withColumn("ingest_ts", F.to_timestamp(F.lit(ingest_ts)))

    # Write to Iceberg
    # Note: bronze_ticks/bronze_codes tables must exist (see docs/10_offline_mainline_A_build_run.md)
    df_ticks = df_tc.unionByName(df_tp)
    df_codes = df_cc.unionByName(df_cp)

    df_ticks.writeTo("lakehouse.options.bronze_ticks").append()
    df_codes.writeTo("lakehouse.options.bronze_codes").append()

    print("OK: ingested to lakehouse.options.bronze_ticks / bronze_codes")

    spark.stop()


if __name__ == "__main__":
    main()
