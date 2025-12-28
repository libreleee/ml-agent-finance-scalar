from __future__ import annotations

from pyspark.sql import functions as F

from spark_jobs.common_spark import build_spark


def main():
    spark = build_spark("etl_bronze_to_silver")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.options")

    # Bronze -> Silver ticks
    b = spark.table("lakehouse.options.bronze_ticks")

    s = (
        b.select(
            "ymcode",
            "side",
            "code",
            "strike",
            F.col("tdate").alias("ts"),
            "tcnt",
            F.col("c").alias("price"),
            F.col("o").alias("open"),
            F.col("h").alias("high"),
            F.col("l").alias("low"),
            "oi",
            "ccnt",
            F.to_date("tdate").alias("trade_date"),
            F.date_trunc("minute", F.col("tdate")).alias("minute_ts"),
            "ingest_ts",
        )
    )

    # Write silver ticks
    s.writeTo("lakehouse.options.silver_ticks").overwritePartitions()

    # dim_contract from codes + inferred strike from code? (샘플 코드 테이블에 strike가 없음)
    # 현재는 codes와 ticks에서 strike를 보조로 붙입니다.
    c = spark.table("lakehouse.options.bronze_codes")
    strike_map = (
        spark.table("lakehouse.options.silver_ticks")
        .select("ymcode", "side", "code", "strike")
        .dropDuplicates(["ymcode", "side", "code"])
    )

    dim = (
        c.join(strike_map, on=["ymcode", "side", "code"], how="left")
         .select(
             "ymcode", "side", "code",
             F.coalesce("strike", F.lit(-1)).alias("strike"),
             "lastday",
             F.to_date(F.lit("1900-01-01")).alias("effective_from"),
             F.to_date(F.lit("2999-12-31")).alias("effective_to"),
         )
    )

    dim.writeTo("lakehouse.options.dim_contract").overwritePartitions()

    print("OK: silver_ticks + dim_contract")
    spark.stop()


if __name__ == "__main__":
    main()
