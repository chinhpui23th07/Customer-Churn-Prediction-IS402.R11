"""Cutoff-safe DuckDB engine for KKBox feature snapshots (Spark schema parity)."""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

from src.kkbox.contract import FEATURE_COLUMNS, WINDOWS


def _build_window_sql(
    raw_root: Path,
    period: str,
    sample_modulus: int,
) -> str:
    win = WINDOWS[period]
    cutoff = win["cutoff"]
    cutoff_dt = datetime.strptime(cutoff, "%Y-%m-%d").date()
    start_30 = (cutoff_dt - timedelta(days=29)).strftime("%Y-%m-%d")
    start_90 = (cutoff_dt - timedelta(days=89)).strftime("%Y-%m-%d")
    source_win = win["source"]

    ch_glob = (raw_root / "churn_label" / "**" / "*.parquet").as_posix().replace("'", "''")
    m_glob = (raw_root / "member" / "**" / "*.parquet").as_posix().replace("'", "''")
    tx_glob = (raw_root / "subscription_transaction" / "**" / "*.parquet").as_posix().replace("'", "''")
    ld_glob = (raw_root / "listening_day" / "**" / "*.parquet").as_posix().replace("'", "''")

    sample_filter = (
        f"AND ABS(HASH(CAST(subscriber_key AS VARCHAR))) % {int(sample_modulus)} = 0"
        if sample_modulus > 1 else ""
    )

    return f"""
    WITH cohort AS (
        SELECT
            CAST(subscriber_key AS VARCHAR) AS subscriber_key,
            CAST(is_churn AS INTEGER) AS is_churn
        FROM read_parquet('{ch_glob}', hive_partitioning=true)
        WHERE label_window = '{source_win}'
        {sample_filter}
    ),
    member_rows AS (
        SELECT
            CAST(subscriber_key AS VARCHAR) AS subscriber_key,
            CAST(registration_month AS DATE) AS registration_month
        FROM read_parquet('{m_glob}')
        WHERE CAST(subscriber_key AS VARCHAR) IN (SELECT subscriber_key FROM cohort)
    ),
    txn_rows AS (
        SELECT
            CAST(subscriber_key AS VARCHAR) AS subscriber_key,
            event_key,
            CAST(transaction_date AS DATE) AS transaction_date,
            CAST(membership_expire_date AS DATE) AS membership_expire_date,
            CAST(actual_amount_paid AS DOUBLE) AS actual_amount_paid,
            CAST(is_auto_renew AS INTEGER) AS is_auto_renew,
            CAST(is_cancel AS INTEGER) AS is_cancel
        FROM read_parquet('{tx_glob}')
        WHERE CAST(transaction_date AS DATE) <= DATE '{cutoff}'
          AND CAST(subscriber_key AS VARCHAR) IN (SELECT subscriber_key FROM cohort)
    ),
    txn_agg AS (
        SELECT
            subscriber_key,
            CAST(SUM(CASE WHEN transaction_date >= DATE '{start_30}' THEN 1 ELSE 0 END) AS INTEGER) AS txn_count_30d,
            CAST(SUM(CASE WHEN transaction_date >= DATE '{start_30}' THEN actual_amount_paid ELSE 0.0 END) AS DOUBLE) AS paid_amount_30d,
            CAST(SUM(CASE WHEN transaction_date >= DATE '{start_90}' AND is_cancel = 1 THEN 1 ELSE 0 END) AS INTEGER) AS cancel_count_90d,
            MAX(transaction_date) AS last_txn_date
        FROM txn_rows
        GROUP BY subscriber_key
    ),
    latest_txn AS (
        SELECT
            subscriber_key,
            last_auto_renew,
            days_until_expiry
        FROM (
            SELECT
                subscriber_key,
                is_auto_renew AS last_auto_renew,
                CAST(DATEDIFF('day', DATE '{cutoff}', membership_expire_date) AS INTEGER) AS days_until_expiry,
                ROW_NUMBER() OVER (
                    PARTITION BY subscriber_key
                    ORDER BY transaction_date DESC, event_key DESC
                ) AS rn
            FROM txn_rows
        ) ranked
        WHERE rn = 1
    ),
    listening_rows AS (
        SELECT
            CAST(subscriber_key AS VARCHAR) AS subscriber_key,
            CAST(activity_date AS DATE) AS activity_date,
            CAST(total_secs AS DOUBLE) AS total_secs
        FROM read_parquet('{ld_glob}', hive_partitioning=true)
        WHERE CAST(activity_date AS DATE) <= DATE '{cutoff}'
          AND CAST(subscriber_key AS VARCHAR) IN (SELECT subscriber_key FROM cohort)
    ),
    listening_agg AS (
        SELECT
            subscriber_key,
            CAST(SUM(CASE WHEN activity_date >= DATE '{start_30}' THEN 1 ELSE 0 END) AS INTEGER) AS active_days_30d,
            CAST(SUM(CASE WHEN activity_date >= DATE '{start_30}' THEN GREATEST(total_secs, 0.0) ELSE 0.0 END) AS DOUBLE) AS listening_secs_30d,
            MAX(activity_date) AS last_listen_date
        FROM listening_rows
        GROUP BY subscriber_key
    )
    SELECT
        c.subscriber_key,
        DATE '{cutoff}' AS as_of_date,
        c.subscriber_key || '|' || '{cutoff}' AS snapshot_key,
        c.is_churn,
        COALESCE(t.txn_count_30d, 0) AS txn_count_30d,
        COALESCE(t.paid_amount_30d, 0.0) AS paid_amount_30d,
        COALESCE(t.cancel_count_90d, 0) AS cancel_count_90d,
        CAST(DATEDIFF('day', t.last_txn_date, DATE '{cutoff}') AS INTEGER) AS days_since_last_txn,
        lt.last_auto_renew,
        lt.days_until_expiry,
        COALESCE(l.active_days_30d, 0) AS active_days_30d,
        COALESCE(l.listening_secs_30d, 0.0) AS listening_secs_30d,
        CAST(DATEDIFF('day', l.last_listen_date, DATE '{cutoff}') AS INTEGER) AS days_since_last_listen,
        CAST(CASE WHEN m.registration_month <= DATE '{cutoff}' THEN DATEDIFF('day', m.registration_month, DATE '{cutoff}') ELSE NULL END AS INTEGER) AS registration_tenure_days,
        CASE WHEN t.last_txn_date IS NOT NULL THEN 1 ELSE 0 END AS has_txn_history,
        CASE WHEN l.last_listen_date IS NOT NULL THEN 1 ELSE 0 END AS has_listening_history
    FROM cohort c
    LEFT JOIN member_rows m ON c.subscriber_key = m.subscriber_key
    LEFT JOIN txn_agg t ON c.subscriber_key = t.subscriber_key
    LEFT JOIN latest_txn lt ON c.subscriber_key = lt.subscriber_key
    LEFT JOIN listening_agg l ON c.subscriber_key = l.subscriber_key
    """


def run_duckdb_snapshot_etl(
    raw_root: Path,
    output_root: Path,
    sample_modulus: int = 1,
    memory_limit: str = "3GB",
) -> dict[str, dict[str, int]]:
    """Build partitioned 2017-02 and 2017-03 KKBox feature snapshots using DuckDB."""
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = (output_root.parent / ".duckdb_kkbox_tmp").resolve()
    tmp_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(database=":memory:")
    con.execute(f"SET memory_limit='{memory_limit}'")
    con.execute(f"SET temp_directory='{tmp_dir.as_posix()}'")
    con.execute("SET preserve_insertion_order=false")
    windows: dict[str, dict[str, int]] = {}
    try:
        for period in WINDOWS:
            part_dir = output_root / f"label_period={period}"
            part_dir.mkdir(parents=True, exist_ok=True)
            out_file = (part_dir / "part-00000.parquet").resolve().as_posix().replace("'", "''")
            sql = _build_window_sql(raw_root, period, sample_modulus)
            con.execute(f"COPY ({sql}) TO '{out_file}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            rows, churn_1, uniq = con.execute(
                f"SELECT COUNT(*), CAST(COALESCE(SUM(is_churn), 0) AS BIGINT), COUNT(DISTINCT snapshot_key) "
                f"FROM read_parquet('{out_file}')"
            ).fetchone()
            schema_cols = [
                r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{out_file}') LIMIT 0").fetchall()
            ]
            missing = [c for c in FEATURE_COLUMNS if c not in schema_cols]
            if missing:
                raise RuntimeError(f"DuckDB snapshot missing contract columns: {missing}")
            windows[period] = {
                "rows": int(rows),
                "churn_1": int(churn_1),
                "unique_snapshots": int(uniq),
            }
    finally:
        con.close()
    return windows
