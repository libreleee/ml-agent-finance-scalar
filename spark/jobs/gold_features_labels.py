from __future__ import annotations

import argparse
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def build_spark(app: str) -> SparkSession:
    return SparkSession.builder.appName(app).getOrCreate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", required=True, help="gold.bars_1m table")
    ap.add_argument("--out_features", required=True, help="gold.features_1m table")
    ap.add_argument("--out_labels", required=True, help="gold.labels_1m table")
    args = ap.parse_args()

    spark = build_spark("gold_features_labels")

    bars = spark.table(args.bars)

    w = Window.partitionBy("ymcode", "cp", "code").orderBy("bar_ts_utc")

    features = (
        bars
        .withColumn("ret_1m", F.log(F.col("close") / F.lag("close", 1).over(w)))
        .withColumn("ret_5m", F.log(F.col("close") / F.lag("close", 5).over(w)))
        .withColumn("mom_15m", F.col("close") / F.lag("close", 15).over(w) - F.lit(1.0))
        .withColumn("oi_chg_5m", F.col("oi_last") - F.lag("oi_last", 5).over(w))
        .withColumn("vol_30m", F.stddev("ret_1m").over(w.rowsBetween(-30, -1)))
        .withColumn("vol_120m", F.stddev("ret_1m").over(w.rowsBetween(-120, -1)))
        # Placeholder for domain features to be joined later:
        .withColumn("iv_atm", F.lit(None).cast("double"))
        .withColumn("iv_skew", F.lit(None).cast("double"))
        .withColumn("delta", F.lit(None).cast("double"))
        .withColumn("gamma", F.lit(None).cast("double"))
        .withColumn("vega", F.lit(None).cast("double"))
        .withColumn("theta", F.lit(None).cast("double"))
        .select(
            "ymcode", "cp", "code", "strike", "bar_ts_utc",
            "ret_1m", "ret_5m", "mom_15m", "oi_chg_5m", "vol_30m", "vol_120m",
            "iv_atm", "iv_skew", "delta", "gamma", "vega", "theta",
            "volume_ticks", "oi_last", "spread_proxy",
        )
    )

    labels = (
        bars
        .withColumn("y_ret_5m", F.log(F.lead("close", 5).over(w) / F.col("close")))
        .withColumn("y_ret_30m", F.log(F.lead("close", 30).over(w) / F.col("close")))
        .withColumn("y_dir_5m", F.when(F.col("y_ret_5m") > 0, 1).when(F.col("y_ret_5m") < 0, -1).otherwise(0))
        .select("ymcode", "cp", "code", "strike", "bar_ts_utc", "y_ret_5m", "y_ret_30m", "y_dir_5m")
    )

    (
        features.writeTo(args.out_features)
        .overwritePartitions()
    )
    (
        labels.writeTo(args.out_labels)
        .overwritePartitions()
    )

    print("[OK] wrote gold features and labels")


if __name__ == "__main__":
    main()
