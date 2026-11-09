"""Axis 2: KKBox 12-Feature Contract, Temporal Cutoff Anti-Leakage & Boundary Verification."""

from __future__ import annotations

import datetime as dt
import inspect
import re
import sys
import types
from pathlib import Path

import duckdb
import pytest

from src.kkbox.contract import ALLOWED_CUTOFFS, FEATURE_COLUMNS, FEATURE_VERSION, WINDOWS
from src.kkbox.features import build_snapshot

MAX_UINT64_STR = "18446744073709551615"


def test_feature_contract_constants_and_markdown_table_parity() -> None:
    assert FEATURE_VERSION == "kkbox-v1"
    assert WINDOWS == {
        "2017-02": {"source": "train", "cutoff": "2017-01-31"},
        "2017-03": {"source": "train_v2", "cutoff": "2017-02-28"},
    }
    assert ALLOWED_CUTOFFS == {"2017-01-31", "2017-02-28"}
    assert len(FEATURE_COLUMNS) == 12
    assert len(set(FEATURE_COLUMNS)) == 12

    md_text = Path("contracts/feature_contract.md").read_text(encoding="utf-8")
    table_features = re.findall(r"^\|\s*`([a-z0-9_]+)`\s*\|", md_text, flags=re.MULTILINE)
    assert table_features == FEATURE_COLUMNS

    for forbidden in ("subscriber_key", "is_churn", "label_period", "snapshot_key", "age_band_start", "gender", "city_code"):
        assert forbidden not in FEATURE_COLUMNS


def test_build_snapshot_input_validation_guards() -> None:
    with pytest.raises(ValueError, match="Unknown label period"):
        build_snapshot(None, None, None, None, "2017-04")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="sample_modulus must be >= 1"):
        build_snapshot(None, None, None, None, "2017-02", sample_modulus=0)  # type: ignore[arg-type]


def test_features_ast_cutoff_and_tiebreak_invariants() -> None:
    source = inspect.getsource(build_snapshot)

    assert "F.date_sub(cutoff, 29)" in source
    assert "F.date_sub(cutoff, 89)" in source
    assert 'F.col("transaction_date") <= cutoff' in source
    assert 'F.col("activity_date") <= cutoff' in source
    assert 'F.col("transaction_date").desc(), F.col("event_key").desc()' in source
    assert 'F.greatest(F.col("total_secs"), F.lit(0.0))' in source
    assert 'F.when(F.col("registration_month") <= cutoff' in source
    assert 'F.concat_ws("|", "subscriber_key", F.lit(window["cutoff"]))' in source

    txn_filter_pos = source.index('F.col("transaction_date") <= cutoff')
    txn_group_pos = source.index('txn_rows.groupBy("subscriber_key")')
    assert txn_filter_pos < txn_group_pos

    listen_filter_pos = source.index('F.col("activity_date") <= cutoff')
    listen_group_pos = source.index('listening_rows.groupBy("subscriber_key")')
    assert listen_filter_pos < listen_group_pos


class _Expr:
    def __init__(self, repr_str: str) -> None:
        self.repr_str = repr_str

    def __repr__(self) -> str:
        return self.repr_str

    def cast(self, dtype: str) -> _Expr:
        return _Expr(f"cast({self.repr_str} as {dtype})")

    def alias(self, name: str) -> _Expr:
        return _Expr(f"{self.repr_str} AS {name}")

    def desc(self) -> _Expr:
        return _Expr(f"{self.repr_str} DESC")

    def isNotNull(self) -> _Expr:
        return _Expr(f"{self.repr_str} IS NOT NULL")

    def otherwise(self, val: object) -> _Expr:
        return _Expr(f"{self.repr_str} ELSE {val}")

    def over(self, win: object) -> _Expr:
        return _Expr(f"{self.repr_str} OVER ({win})")

    def __eq__(self, other: object) -> _Expr:  # type: ignore[override]
        return _Expr(f"({self.repr_str} == {other})")

    def __le__(self, other: object) -> _Expr:
        return _Expr(f"({self.repr_str} <= {other})")

    def __ge__(self, other: object) -> _Expr:
        return _Expr(f"({self.repr_str} >= {other})")

    def __and__(self, other: object) -> _Expr:
        return _Expr(f"({self.repr_str} AND {other})")


class _FakeDF:
    def __init__(self, name: str, ops: list[tuple[str, object]] | None = None) -> None:
        self.name = name
        self.ops = list(ops or [])

    def where(self, cond: object) -> _FakeDF:
        return _FakeDF(self.name, [*self.ops, ("where", str(cond))])

    def select(self, *cols: object) -> _FakeDF:
        return _FakeDF(self.name, [*self.ops, ("select", [str(c) for c in cols])])

    def join(self, other: _FakeDF, on: str, how: str) -> _FakeDF:
        return _FakeDF(self.name, [*self.ops, ("join", (other.name, on, how, other.ops))])

    def groupBy(self, col: str) -> _FakeDF:
        return _FakeDF(self.name, [*self.ops, ("groupBy", col)])

    def agg(self, *exprs: object) -> _FakeDF:
        return _FakeDF(self.name, [*self.ops, ("agg", [str(e) for e in exprs])])

    def withColumn(self, name: str, expr: object) -> _FakeDF:
        return _FakeDF(self.name, [*self.ops, ("withColumn", (name, str(expr)))])


def test_build_snapshot_dataframe_dag_construction_and_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_f = types.SimpleNamespace(
        to_date=lambda x: _Expr(f"to_date({x})"),
        lit=lambda x: _Expr(f"lit({x})"),
        date_sub=lambda c, d: _Expr(f"date_sub({c},{d})"),
        col=lambda c: _Expr(f"col({c})"),
        pmod=lambda a, b: _Expr(f"pmod({a},{b})"),
        xxhash64=lambda c: _Expr(f"xxhash64({c})"),
        sum=lambda e: _Expr(f"sum({e})"),
        when=lambda c, v: _Expr(f"CASE WHEN {c} THEN {v}"),
        max=lambda c: _Expr(f"max({c})"),
        row_number=lambda: _Expr("row_number()"),
        datediff=lambda a, b: _Expr(f"datediff({a},{b})"),
        greatest=lambda a, b: _Expr(f"greatest({a},{b})"),
        concat_ws=lambda sep, a, b: _Expr(f"concat_ws({sep},{a},{b})"),
        coalesce=lambda a, b: _Expr(f"coalesce({a},{b})"),
    )

    class _FakeWin:
        @staticmethod
        def partitionBy(col: str) -> _FakeWin:
            return _FakeWin()

        def orderBy(self, *cols: object) -> str:
            return ",".join(str(c) for c in cols)

    fake_pyspark_sql = types.ModuleType("pyspark.sql")
    fake_pyspark_sql.Window = _FakeWin  # type: ignore[attr-defined]
    fake_pyspark_sql.functions = fake_f  # type: ignore[attr-defined]
    fake_pyspark = types.ModuleType("pyspark")
    fake_pyspark.sql = fake_pyspark_sql  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "pyspark", fake_pyspark)
    monkeypatch.setitem(sys.modules, "pyspark.sql", fake_pyspark_sql)

    out_full = build_snapshot(
        _FakeDF("labels"), _FakeDF("members"), _FakeDF("txns"), _FakeDF("listening"),
        "2017-02", sample_modulus=1,
    )
    final_select = out_full.ops[-1][1]
    assert len(final_select) == 17  # 5 key/label cols + 12 FEATURE_COLUMNS

    out_pilot = build_snapshot(
        _FakeDF("labels"), _FakeDF("members"), _FakeDF("txns"), _FakeDF("listening"),
        "2017-03", sample_modulus=20,
    )
    where_clauses = [op[1] for op in out_pilot.ops if op[0] == "where"]
    assert any("pmod(xxhash64(subscriber_key),lit(20))" in w for w in where_clauses)


def _run_duckdb_reference_snapshot(cutoff_str: str, source_window: str, label_period: str) -> dict[str, dict]:
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE labels (subscriber_key VARCHAR, label_window VARCHAR, is_churn INTEGER);
        CREATE TABLE members (subscriber_key VARCHAR, registration_month DATE);
        CREATE TABLE txns (
            subscriber_key VARCHAR, event_key BIGINT, transaction_date DATE,
            membership_expire_date DATE, actual_amount_paid DOUBLE,
            is_auto_renew INTEGER, is_cancel INTEGER
        );
        CREATE TABLE listening (subscriber_key VARCHAR, activity_date DATE, total_secs DOUBLE);
    """)
    con.executemany(
        "INSERT INTO labels VALUES (?, ?, ?)",
        [(MAX_UINT64_STR, "train", 1), ("200", "train", 0), ("300", "train", 1), (MAX_UINT64_STR, "train_v2", 0)],
    )
    con.executemany(
        "INSERT INTO members VALUES (?, ?)",
        [(MAX_UINT64_STR, dt.date(2016, 1, 1)), ("200", dt.date(2017, 3, 1)), ("300", dt.date(2017, 1, 1))],
    )
    con.executemany(
        "INSERT INTO txns VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (MAX_UINT64_STR, 1, dt.date(2016, 11, 2), dt.date(2016, 12, 2), 99.0, 1, 1),
            (MAX_UINT64_STR, 2, dt.date(2016, 11, 3), dt.date(2016, 12, 3), 99.0, 1, 1),
            (MAX_UINT64_STR, 3, dt.date(2017, 1, 1), dt.date(2017, 1, 31), 100.0, 1, 0),
            (MAX_UINT64_STR, 4, dt.date(2017, 1, 2), dt.date(2017, 2, 1), 120.0, 0, 0),
            (MAX_UINT64_STR, 10, dt.date(2017, 1, 20), dt.date(2017, 2, 10), 50.0, 0, 0),
            (MAX_UINT64_STR, 11, dt.date(2017, 1, 20), dt.date(2017, 2, 20), 149.0, 1, 0),
            (MAX_UINT64_STR, 99, dt.date(2017, 2, 1), dt.date(2017, 3, 15), 999.0, 0, 1),
            ("300", 5, dt.date(2016, 8, 1), dt.date(2016, 9, 1), 149.0, 0, 1),
        ],
    )
    con.executemany(
        "INSERT INTO listening VALUES (?, ?, ?)",
        [
            (MAX_UINT64_STR, dt.date(2017, 1, 1), 500.0),
            (MAX_UINT64_STR, dt.date(2017, 1, 2), -45.0),
            (MAX_UINT64_STR, dt.date(2017, 1, 31), 180.5),
            (MAX_UINT64_STR, dt.date(2017, 2, 2), 9999.0),
        ],
    )
    query = """
    WITH params AS (
        SELECT CAST(? AS DATE) AS cutoff,
               CAST(? AS DATE) - INTERVAL 29 DAY AS start_30,
               CAST(? AS DATE) - INTERVAL 89 DAY AS start_90
    ),
    cohort AS (SELECT subscriber_key, is_churn FROM labels WHERE label_window = ?),
    txn_rows AS (
        SELECT t.* FROM txns t, params p
        WHERE t.transaction_date <= p.cutoff AND t.subscriber_key IN (SELECT subscriber_key FROM cohort)
    ),
    txn_agg AS (
        SELECT subscriber_key,
               SUM(CASE WHEN transaction_date >= p.start_30 THEN 1 ELSE 0 END) AS txn_count_30d,
               SUM(CASE WHEN transaction_date >= p.start_30 THEN actual_amount_paid ELSE 0.0 END) AS paid_amount_30d,
               SUM(CASE WHEN transaction_date >= p.start_90 AND is_cancel = 1 THEN 1 ELSE 0 END) AS cancel_count_90d,
               MAX(transaction_date) AS last_txn_date
        FROM txn_rows, params p GROUP BY subscriber_key
    ),
    latest_txn AS (
        SELECT subscriber_key, is_auto_renew AS last_auto_renew,
               DATE_DIFF('day', p.cutoff, membership_expire_date) AS days_until_expiry
        FROM (
            SELECT t.*, ROW_NUMBER() OVER (
                PARTITION BY subscriber_key ORDER BY transaction_date DESC, event_key DESC
            ) AS rnk FROM txn_rows t
        ) ranked, params p WHERE rnk = 1
    ),
    listen_rows AS (
        SELECT l.* FROM listening l, params p
        WHERE l.activity_date <= p.cutoff AND l.subscriber_key IN (SELECT subscriber_key FROM cohort)
    ),
    listen_agg AS (
        SELECT subscriber_key,
               SUM(CASE WHEN activity_date >= p.start_30 THEN 1 ELSE 0 END) AS active_days_30d,
               SUM(CASE WHEN activity_date >= p.start_30 THEN GREATEST(total_secs, 0.0) ELSE 0.0 END) AS listening_secs_30d,
               MAX(activity_date) AS last_listen_date
        FROM listen_rows, params p GROUP BY subscriber_key
    )
    SELECT c.subscriber_key, ? AS label_period, p.cutoff AS as_of_date,
           c.subscriber_key || '|' || ? AS snapshot_key, c.is_churn,
           COALESCE(ta.txn_count_30d, 0) AS txn_count_30d,
           COALESCE(ta.paid_amount_30d, 0.0) AS paid_amount_30d,
           COALESCE(ta.cancel_count_90d, 0) AS cancel_count_90d,
           DATE_DIFF('day', ta.last_txn_date, p.cutoff) AS days_since_last_txn,
           lt.last_auto_renew, lt.days_until_expiry,
           COALESCE(la.active_days_30d, 0) AS active_days_30d,
           COALESCE(la.listening_secs_30d, 0.0) AS listening_secs_30d,
           DATE_DIFF('day', la.last_listen_date, p.cutoff) AS days_since_last_listen,
           CASE WHEN m.registration_month <= p.cutoff THEN DATE_DIFF('day', m.registration_month, p.cutoff) END AS registration_tenure_days,
           CASE WHEN ta.last_txn_date IS NOT NULL THEN 1 ELSE 0 END AS has_txn_history,
           CASE WHEN la.last_listen_date IS NOT NULL THEN 1 ELSE 0 END AS has_listening_history
    FROM cohort c CROSS JOIN params p
    LEFT JOIN members m ON c.subscriber_key = m.subscriber_key
    LEFT JOIN txn_agg ta ON c.subscriber_key = ta.subscriber_key
    LEFT JOIN latest_txn lt ON c.subscriber_key = lt.subscriber_key
    LEFT JOIN listen_agg la ON c.subscriber_key = la.subscriber_key
    """
    cursor = con.execute(query, [cutoff_str, cutoff_str, cutoff_str, source_window, label_period, cutoff_str])
    cols = [d[0] for d in cursor.description]
    return {row[0]: dict(zip(cols, row)) for row in cursor.fetchall()}


def test_duckdb_reference_cutoff_and_boundary_math() -> None:
    feb = _run_duckdb_reference_snapshot("2017-01-31", "train", "2017-02")
    row_max = feb[MAX_UINT64_STR]
    assert row_max["snapshot_key"] == f"{MAX_UINT64_STR}|2017-01-31"
    assert row_max["txn_count_30d"] == 3
    assert row_max["paid_amount_30d"] == pytest.approx(319.0)
    assert row_max["cancel_count_90d"] == 1
    assert row_max["days_since_last_txn"] == 11
    assert row_max["last_auto_renew"] == 1
    assert row_max["days_until_expiry"] == 20
    assert row_max["active_days_30d"] == 2
    assert row_max["listening_secs_30d"] == pytest.approx(180.5)
    assert row_max["days_since_last_listen"] == 0
    assert row_max["registration_tenure_days"] == 396
    assert row_max["has_txn_history"] == 1
    assert row_max["has_listening_history"] == 1

    cold = feb["200"]
    assert cold["txn_count_30d"] == 0
    assert cold["days_since_last_txn"] is None
    assert cold["last_auto_renew"] is None
    assert cold["days_until_expiry"] is None
    assert cold["days_since_last_listen"] is None
    assert cold["registration_tenure_days"] is None
    assert cold["has_txn_history"] == 0
    assert cold["has_listening_history"] == 0

    old_only = feb["300"]
    assert old_only["txn_count_30d"] == 0
    assert old_only["cancel_count_90d"] == 0
    assert old_only["has_txn_history"] == 1
    assert old_only["days_since_last_txn"] == 183
    assert old_only["days_until_expiry"] == -152

    mar = _run_duckdb_reference_snapshot("2017-02-28", "train_v2", "2017-03")
    row_mar = mar[MAX_UINT64_STR]
    assert row_mar["last_auto_renew"] == 0
    assert row_mar["days_since_last_txn"] == 27
    assert row_mar["days_since_last_listen"] == 26
    assert row_mar["listening_secs_30d"] == pytest.approx(10179.5)
