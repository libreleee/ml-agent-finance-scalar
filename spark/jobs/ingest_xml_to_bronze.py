from __future__ import annotations

import argparse
import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T

from spark.utils.xml_rowtag import infer_row_tag


def build_spark(app: str) -> SparkSession:
    return (
        SparkSession.builder
        .appName(app)
        .getOrCreate()
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="XML file path")
    ap.add_argument("--table", required=True, help="Iceberg table name, e.g., bronze.raw_ticks")
    ap.add_argument("--cp", default=None, help="CALL or PUT. If omitted, inferred from filename.")
    args = ap.parse_args()

    xml_path = args.input
    table = args.table

    cp = args.cp
    if cp is None:
        name = os.path.basename(xml_path).upper()
        if "CALL" in name:
            cp = "CALL"
        elif "PUT" in name:
            cp = "PUT"
        else:
            cp = "NA"

    row_tag = infer_row_tag(xml_path)

    spark = build_spark("ingest_xml_to_bronze")

    df = (
        spark.read.format("xml")
        .option("rowTag", row_tag)
        .load(xml_path)
    )

    # Common metadata columns
    df = (
        df
        .withColumn("ingest_ts", F.current_timestamp())
        .withColumn("source_file", F.lit(os.path.basename(xml_path)))
        .withColumn("cp", F.lit(cp))
    )

    # Normalize timestamps if present
    if "tdate" in df.columns:
        # tdate looks like 2025-12-01T10:01:13+09:00
        df = df.withColumn("ts_local", F.to_timestamp("tdate"))
        df = df.withColumn("ts_utc", F.to_utc_timestamp(F.col("ts_local"), "Asia/Seoul"))

    # Cast common numeric types if present
    cast_map = {
        "strike": "double",
        "idate": "int",
        "itime": "int",
        "tcnt": "int",
        "c": "double",
        "o": "double",
        "h": "double",
        "l": "double",
        "oi": "double",
        "ccnt": "int",
        "lastday": "int",
    }
    for col, typ in cast_map.items():
        if col in df.columns:
            df = df.withColumn(col, F.col(col).cast(typ))

    # Append to Iceberg table
    # NOTE: Your Spark session must be configured with Iceberg catalog.
    (
        df.writeTo(table)
        .append()
    )

    print(f"[OK] ingested {xml_path} as rowTag={row_tag} into {table} (cp={cp})")


if __name__ == "__main__":
    main()
