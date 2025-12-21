from __future__ import annotations

import argparse
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def build_spark(app: str) -> SparkSession:
    return SparkSession.builder.appName(app).getOrCreate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", required=True, help="bronze.raw_ticks table")
    ap.add_argument("--codes", required=True, help="bronze.raw_codes table")
    ap.add_argument("--out_ticks", required=True, help="silver.ticks table")
    ap.add_argument("--out_dim", required=True, help="silver.dim_contract table")
    args = ap.parse_args()

    spark = build_spark("bronze_to_silver")

    raw_ticks = spark.table(args.ticks)
    raw_codes = spark.table(args.codes)

    # Deduplicate ticks by (ymcode, cp, code, ts_utc) keeping latest ingest_ts
    w = Window.partitionBy("ymcode", "cp", "code", "ts_utc").orderBy(F.col("ingest_ts").desc())
    ticks = (
        raw_ticks
        .withColumn("rn", F.row_number().over(w))
        .filter(F.col("rn") == 1)
        .drop("rn")
    )

    # Standardize
    ticks = (
        ticks
        .withColumn("price", F.col("c").cast("double"))
        .select(
            "ymcode", "cp", "code",
            F.col("strike").cast("double").alias("strike"),
            "ts_utc",
            "price",
            F.col("o").cast("double").alias("o"),
            F.col("h").cast("double").alias("h"),
            F.col("l").cast("double").alias("l"),
            F.col("oi").cast("double").alias("oi"),
            F.col("tcnt").cast("int").alias("tcnt"),
            F.col("ccnt").cast("int").alias("ccnt"),
            "source_file",
            "ingest_ts",
        )
    )

    (
        ticks.writeTo(args.out_ticks)
        .overwritePartitions()
    )

    # dim_contract: join strike_from_code if present
    codes = (
        raw_codes
        .select(
            "ymcode", "cp", "code",
            F.col("lastday").cast("double").alias("strike_from_code")
        )
        .dropna(subset=["ymcode", "cp", "code"])
        .dropDuplicates(["ymcode", "cp", "code"])
    )

    dim = (
        ticks.groupBy("ymcode", "cp", "code")
        .agg(
            F.max("strike").alias("strike"),
            F.min("ts_utc").alias("first_seen_ts_utc"),
            F.max("ts_utc").alias("last_seen_ts_utc"),
        )
        .join(codes, on=["ymcode", "cp", "code"], how="left")
        .select(
            "ymcode", "cp", "code",
            "strike",
            "strike_from_code",
            "first_seen_ts_utc",
            "last_seen_ts_utc",
        )
    )

    (
        dim.writeTo(args.out_dim)
        .overwritePartitions()
    )

    print("[OK] wrote silver.ticks and silver.dim_contract")


if __name__ == "__main__":
    main()
