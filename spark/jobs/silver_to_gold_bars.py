from __future__ import annotations

import argparse
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def build_spark(app: str) -> SparkSession:
    return SparkSession.builder.appName(app).getOrCreate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", required=True, help="silver.ticks table")
    ap.add_argument("--out", required=True, help="gold.bars_1m table")
    ap.add_argument("--bar_seconds", type=int, default=60, help="bar size in seconds")
    args = ap.parse_args()

    spark = build_spark("silver_to_gold_bars")

    ticks = spark.table(args.ticks)

    # Bucket ts_utc to minute bars
    bar_ts = F.from_unixtime((F.unix_timestamp("ts_utc") / args.bar_seconds).cast("long") * args.bar_seconds).cast("timestamp")
    df = ticks.withColumn("bar_ts_utc", bar_ts)

    # OHLC using aggregations
    # NOTE: True OHLC requires ordering; for minute bars from tick price you can approximate as:
    # open = first(price), close = last(price), high = max(price), low = min(price)
    # We use Spark aggregate with sort within group using min/max ts.
    agg = (
        df.groupBy("ymcode", "cp", "code", "bar_ts_utc")
        .agg(
            F.max("strike").alias("strike"),
            F.min(F.struct("ts_utc", "price")).alias("open_struct"),
            F.max(F.struct("ts_utc", "price")).alias("close_struct"),
            F.max("price").alias("high"),
            F.min("price").alias("low"),
            F.sum(F.coalesce("tcnt", F.lit(0))).cast("int").alias("volume_ticks"),
            F.max("oi").alias("oi_last"),
        )
        .withColumn("open", F.col("open_struct.price"))
        .withColumn("close", F.col("close_struct.price"))
        .drop("open_struct", "close_struct")
        .withColumn("spread_proxy", F.lit(None).cast("double"))
        .select(
            "ymcode", "cp", "code", "strike",
            "bar_ts_utc",
            "open", "high", "low", "close",
            "volume_ticks", "oi_last",
            "spread_proxy",
        )
    )

    (
        agg.writeTo(args.out)
        .overwritePartitions()
    )

    print("[OK] wrote gold bars")


if __name__ == "__main__":
    main()
