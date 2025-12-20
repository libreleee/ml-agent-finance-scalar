from __future__ import annotations

import argparse
from pyspark.sql import functions as F, Window

from spark_jobs.common_spark import build_spark


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bar-interval", default="1m", choices=["1m"])
    args = ap.parse_args()

    spark = build_spark("features_silver_to_gold")

    s = spark.table("lakehouse.options.silver_ticks")

    # 1m bars
    w_bar = Window.partitionBy("ymcode", "side", "code", "strike", "minute_ts").orderBy(F.col("ts").asc())

    bars = (
        s.withColumn("rn_asc", F.row_number().over(w_bar))
         .withColumn("rn_desc", F.row_number().over(w_bar.orderBy(F.col("ts").desc())))
         .groupBy("ymcode", "side", "code", "strike", F.col("minute_ts").alias("bar_ts"), "trade_date")
         .agg(
             F.first(F.when(F.col("rn_asc") == 1, F.col("open")), ignorenulls=True).alias("o"),
             F.max("high").alias("h"),
             F.min("low").alias("l"),
             F.first(F.when(F.col("rn_desc") == 1, F.col("price")), ignorenulls=True).alias("c"),
             F.count("*").alias("tick_count"),
             F.sum(F.col("ccnt").cast("long")).alias("v"),
             F.first(F.when(F.col("rn_desc") == 1, F.col("oi")), ignorenulls=True).alias("oi_last"),
         )
    )

    bars.writeTo("lakehouse.options.gold_bars_1m").overwritePartitions()

    # Features from bars (simple baseline)
    w_entity = Window.partitionBy("ymcode", "side", "code", "strike").orderBy(F.col("bar_ts").asc())

    bars2 = (
        bars
        .withColumn("c_lag1", F.lag("c", 1).over(w_entity))
        .withColumn("c_lag5", F.lag("c", 5).over(w_entity))
        .withColumn("oi_lag5", F.lag("oi_last", 5).over(w_entity))
        .withColumn("ret_1", F.when(F.col("c_lag1").isNull(), F.lit(None))
                           .otherwise(F.col("c") / F.col("c_lag1") - 1.0))
        .withColumn("ret_5", F.when(F.col("c_lag5").isNull(), F.lit(None))
                           .otherwise(F.col("c") / F.col("c_lag5") - 1.0))
        .withColumn("range_1", (F.col("h") - F.col("l")) / F.col("c"))
        .withColumn("oi_chg_5", F.when(F.col("oi_lag5").isNull(), F.lit(None))
                              .otherwise(F.col("oi_last") - F.col("oi_lag5")))
    )

    # rolling volatility over 20 bars
    w20 = w_entity.rowsBetween(-19, 0)
    feats = (
        bars2
        .withColumn("f_vol_20", F.stddev_samp("ret_1").over(w20))
        .withColumn("f_range_5", F.avg("range_1").over(w_entity.rowsBetween(-4, 0)))
        .withColumn("f_spread_proxy", F.avg("range_1").over(w_entity.rowsBetween(-4, 0)))
        .withColumn("f_iv_proxy", F.col("f_vol_20"))  # placeholder
        .select(
            "ymcode","side","code","strike",
            F.col("bar_ts").alias("asof_ts"),
            F.col("ret_1").alias("f_ret_1"),
            F.col("ret_5").alias("f_ret_5"),
            F.col("f_vol_20"),
            F.col("f_range_5"),
            F.col("oi_chg_5").alias("f_oi_chg_5"),
            "f_spread_proxy",
            "f_iv_proxy",
            "trade_date"
        )
    )

    feats.writeTo("lakehouse.options.gold_features_1m").overwritePartitions()

    # Labels (forward returns)
    w_fwd = Window.partitionBy("ymcode","side","code","strike").orderBy(F.col("asof_ts").asc())
    labels = (
        feats
        .withColumn("c_now", F.col("f_ret_1")*0 + 1)  # placeholder to keep schema stable (we will join back to bars for c)
    )

    # Use bars close for label
    bars_close = bars.select("ymcode","side","code","strike", F.col("bar_ts").alias("asof_ts"), F.col("c").alias("close"))
    ds = feats.join(bars_close, on=["ymcode","side","code","strike","asof_ts"], how="left")

    w_ds = Window.partitionBy("ymcode","side","code","strike").orderBy(F.col("asof_ts").asc())
    ds2 = (
        ds.withColumn("close_fwd5", F.lead("close", 5).over(w_ds))
          .withColumn("close_fwd15", F.lead("close", 15).over(w_ds))
          .withColumn("y_fwd_ret_5", F.when(F.col("close_fwd5").isNull(), F.lit(None))
                                   .otherwise(F.col("close_fwd5") / F.col("close") - 1.0))
          .withColumn("y_fwd_ret_15", F.when(F.col("close_fwd15").isNull(), F.lit(None))
                                    .otherwise(F.col("close_fwd15") / F.col("close") - 1.0))
          .select("ymcode","side","code","strike","asof_ts","y_fwd_ret_5","y_fwd_ret_15","trade_date")
    )

    ds2.writeTo("lakehouse.options.gold_labels_1m").overwritePartitions()

    print("OK: gold_bars_1m / gold_features_1m / gold_labels_1m")
    spark.stop()


if __name__ == "__main__":
    main()
