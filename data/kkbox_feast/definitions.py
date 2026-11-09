"""Feast definitions for cutoff-specific KKBox feature snapshots."""

from pathlib import Path

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float64, Int32
from feast.value_type import ValueType

ROOT = Path(__file__).resolve().parent

snapshot = Entity(
    name="snapshot_key",
    join_keys=["snapshot_key"],
    value_type=ValueType.STRING,
    description="subscriber_key|as_of_date; one historical cutoff per online key",
)

source = FileSource(
    name="kkbox_feature_source",
    path=(ROOT / "churn_features.parquet").as_posix(),
    timestamp_field="event_timestamp",
)

feature_view = FeatureView(
    name="kkbox_churn_features",
    entities=[snapshot],
    ttl=None,
    online=True,
    offline=True,
    source=source,
    schema=[
        Field(name="txn_count_30d", dtype=Int32),
        Field(name="paid_amount_30d", dtype=Float64),
        Field(name="cancel_count_90d", dtype=Int32),
        Field(name="days_since_last_txn", dtype=Int32),
        Field(name="last_auto_renew", dtype=Int32),
        Field(name="days_until_expiry", dtype=Int32),
        Field(name="active_days_30d", dtype=Int32),
        Field(name="listening_secs_30d", dtype=Float64),
        Field(name="days_since_last_listen", dtype=Int32),
        Field(name="registration_tenure_days", dtype=Int32),
        Field(name="has_txn_history", dtype=Int32),
        Field(name="has_listening_history", dtype=Int32),
    ],
)
