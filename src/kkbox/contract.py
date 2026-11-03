"""Shared KKBox feature and cutoff contract for ETL, training and serving."""

WINDOWS = {
    "2017-02": {"source": "train", "cutoff": "2017-01-31"},
    "2017-03": {"source": "train_v2", "cutoff": "2017-02-28"},
}

ALLOWED_CUTOFFS = {window["cutoff"] for window in WINDOWS.values()}
FEATURE_VERSION = "kkbox-v1"
FEATURE_COLUMNS = [
    "txn_count_30d", "paid_amount_30d", "cancel_count_90d",
    "days_since_last_txn", "last_auto_renew", "days_until_expiry",
    "active_days_30d", "listening_secs_30d", "days_since_last_listen",
    "registration_tenure_days", "has_txn_history", "has_listening_history",
]
