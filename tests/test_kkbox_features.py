"""Verify KKBox feature cutoffs with events on both sides of the boundary."""

from datetime import date

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DateType, DoubleType, IntegerType, LongType, StringType, StructField, StructType,
)

from src.kkbox.features import FEATURE_COLUMNS, build_snapshot


@pytest.fixture(scope="module")
def spark():
    session = (SparkSession.builder.master("local[1]").appName("kkbox-feature-tests")
               .config("spark.ui.enabled", "false")
               .config("spark.sql.shuffle.partitions", "2")
               .getOrCreate())
    yield session
    session.stop()


def frame(spark, fields, rows):
    return spark.createDataFrame(rows, StructType([StructField(*field) for field in fields]))


def test_cutoff_excludes_future_events_and_preserves_window_key(spark):
    labels = frame(spark, [
        ("subscriber_key", LongType(), False), ("label_window", StringType(), False),
        ("is_churn", IntegerType(), False),
    ], [(1, "train", 1), (2, "train", 0), (1, "train_v2", 0)])
    members = frame(spark, [
        ("subscriber_key", LongType(), False), ("registration_month", DateType(), True),
    ], [(1, date(2016, 1, 1)), (2, None)])
    transactions = frame(spark, [
        ("subscriber_key", LongType(), False), ("event_key", LongType(), False),
        ("transaction_date", DateType(), False), ("membership_expire_date", DateType(), False),
        ("actual_amount_paid", IntegerType(), False), ("is_auto_renew", IntegerType(), False),
        ("is_cancel", IntegerType(), False),
    ], [
        (1, 1, date(2017, 1, 15), date(2017, 2, 15), 10, 1, 0),
        (1, 2, date(2017, 2, 2), date(2017, 3, 2), 100, 0, 0),
        (1, 3, date(2017, 2, 28), date(2017, 2, 28), 0, 0, 1),
        (2, 4, date(2017, 1, 30), date(2017, 2, 28), 20, 1, 0),
    ])
    listening = frame(spark, [
        ("subscriber_key", LongType(), False), ("activity_date", DateType(), False),
        ("total_secs", DoubleType(), False),
    ], [
        (1, date(2017, 1, 31), 30.0),
        (1, date(2017, 2, 1), 300.0),
        (2, date(2017, 1, 30), 5.0),
    ])

    feb = {row["subscriber_key"]: row.asDict() for row in
           build_snapshot(labels, members, transactions, listening, "2017-02").collect()}
    mar = {row["subscriber_key"]: row.asDict() for row in
           build_snapshot(labels, members, transactions, listening, "2017-03").collect()}

    assert set(feb) == {"1", "2"}
    assert feb["1"]["snapshot_key"] == "1|2017-01-31"
    assert feb["1"]["txn_count_30d"] == 1
    assert feb["1"]["paid_amount_30d"] == 10.0
    assert feb["1"]["active_days_30d"] == 1
    assert feb["1"]["listening_secs_30d"] == 30.0
    assert feb["1"]["last_auto_renew"] == 1
    assert feb["1"]["days_until_expiry"] == 15
    assert feb["1"]["is_churn"] == 1
    assert mar["1"]["snapshot_key"] == "1|2017-02-28"
    assert mar["1"]["txn_count_30d"] == 2
    assert mar["1"]["cancel_count_90d"] == 1
    assert mar["1"]["active_days_30d"] == 2
    assert mar["1"]["is_churn"] == 0
    assert set(FEATURE_COLUMNS).issubset(feb["1"])
