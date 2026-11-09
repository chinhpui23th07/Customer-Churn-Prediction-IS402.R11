"""Cutoff-safe Spark features for the official KKBox churn labels."""

from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from src.kkbox.contract import FEATURE_COLUMNS, WINDOWS


def build_snapshot(
    labels: DataFrame,
    members: DataFrame,
    transactions: DataFrame,
    listening: DataFrame,
    label_period: str,
    sample_modulus: int = 1,
) -> DataFrame:
    """Return one feature row per labeled subscriber at the period cutoff."""
    if label_period not in WINDOWS:
        raise ValueError(f"Unknown label period: {label_period}")
    if sample_modulus < 1:
        raise ValueError("sample_modulus must be >= 1")
    window = WINDOWS[label_period]
    cutoff = F.to_date(F.lit(window["cutoff"]))
    start_30 = F.date_sub(cutoff, 29)
    start_90 = F.date_sub(cutoff, 89)

    cohort = (
        labels.where(F.col("label_window") == window["source"])
        .select(F.col("subscriber_key").cast("string").alias("subscriber_key"),
                F.col("is_churn").cast("int").alias("is_churn"))
    )
    if sample_modulus > 1:
        cohort = cohort.where(F.pmod(F.xxhash64("subscriber_key"), F.lit(sample_modulus)) == 0)
    keys = cohort.select("subscriber_key")

    member_rows = (
        members.select(F.col("subscriber_key").cast("string").alias("subscriber_key"),
                       F.col("registration_month"))
        .join(keys, "subscriber_key", "left_semi")
    )
    txn_rows = (
        transactions.select(
            F.col("subscriber_key").cast("string").alias("subscriber_key"),
            "event_key", "transaction_date", "membership_expire_date",
            "actual_amount_paid", "is_auto_renew", "is_cancel",
        )
        .where(F.col("transaction_date") <= cutoff)
        .join(keys, "subscriber_key", "left_semi")
    )
    txn_agg = txn_rows.groupBy("subscriber_key").agg(
        F.sum(F.when(F.col("transaction_date") >= start_30, 1).otherwise(0)).alias("txn_count_30d"),
        F.sum(F.when(F.col("transaction_date") >= start_30, F.col("actual_amount_paid"))
              .otherwise(0)).cast("double").alias("paid_amount_30d"),
        F.sum(F.when((F.col("transaction_date") >= start_90) & (F.col("is_cancel") == 1), 1)
              .otherwise(0)).alias("cancel_count_90d"),
        F.max("transaction_date").alias("last_txn_date"),
    )
    latest_txn = (
        txn_rows.withColumn("rank", F.row_number().over(
            Window.partitionBy("subscriber_key").orderBy(
                F.col("transaction_date").desc(), F.col("event_key").desc())))
        .where(F.col("rank") == 1)
        .select("subscriber_key", F.col("is_auto_renew").cast("int").alias("last_auto_renew"),
                F.datediff("membership_expire_date", cutoff).alias("days_until_expiry"))
    )

    listening_rows = (
        listening.select(F.col("subscriber_key").cast("string").alias("subscriber_key"),
                         "activity_date", "total_secs")
        .where(F.col("activity_date") <= cutoff)
        .join(keys, "subscriber_key", "left_semi")
    )
    listening_agg = listening_rows.groupBy("subscriber_key").agg(
        F.sum(F.when(F.col("activity_date") >= start_30, 1).otherwise(0)).alias("active_days_30d"),
        F.sum(F.when(F.col("activity_date") >= start_30,
                     F.greatest(F.col("total_secs"), F.lit(0.0))).otherwise(0.0))
        .alias("listening_secs_30d"),
        F.max("activity_date").alias("last_listen_date"),
    )

    joined = (
        cohort.join(member_rows, "subscriber_key", "left")
        .join(txn_agg, "subscriber_key", "left")
        .join(latest_txn, "subscriber_key", "left")
        .join(listening_agg, "subscriber_key", "left")
    )
    result = joined.select(
        "subscriber_key",
        F.lit(label_period).alias("label_period"),
        cutoff.alias("as_of_date"),
        F.concat_ws("|", "subscriber_key", F.lit(window["cutoff"])).alias("snapshot_key"),
        F.col("is_churn"),
        F.coalesce("txn_count_30d", F.lit(0)).cast("int").alias("txn_count_30d"),
        F.coalesce("paid_amount_30d", F.lit(0.0)).alias("paid_amount_30d"),
        F.coalesce("cancel_count_90d", F.lit(0)).cast("int").alias("cancel_count_90d"),
        F.datediff(cutoff, "last_txn_date").alias("days_since_last_txn"),
        "last_auto_renew", "days_until_expiry",
        F.coalesce("active_days_30d", F.lit(0)).cast("int").alias("active_days_30d"),
        F.coalesce("listening_secs_30d", F.lit(0.0)).alias("listening_secs_30d"),
        F.datediff(cutoff, "last_listen_date").alias("days_since_last_listen"),
        F.when(F.col("registration_month") <= cutoff,
               F.datediff(cutoff, "registration_month")).alias("registration_tenure_days"),
        F.when(F.col("last_txn_date").isNotNull(), 1).otherwise(0).alias("has_txn_history"),
        F.when(F.col("last_listen_date").isNotNull(), 1).otherwise(0).alias("has_listening_history"),
    )
    return result
