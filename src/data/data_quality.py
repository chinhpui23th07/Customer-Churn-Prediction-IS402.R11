"""
Module kiểm định chất lượng dữ liệu nâng cao (Advanced Data Quality & Outlier Detection).
Hiện thực phát hiện dị biệt (IQR, Z-score) và xác thực hợp đồng dữ liệu (Data Contracts).
Tuân thủ Invariant 01 (Clean Architecture) và Invariant 02 (< 400 dòng).
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
TRAIN_PARQUET = os.path.join(PROCESSED_DIR, "train_features.parquet")
OUTPUT_QUALITY_JSON = os.path.join(PROCESSED_DIR, "data_quality_report.json")

NUMERIC_COLS = [
    "age", "tenure", "usage_frequency", "support_calls",
    "payment_delay", "total_spend", "last_interaction"
]

FEATURE_BOUNDS = {
    "age": (18.0, 100.0),
    "tenure": (0.0, 120.0),
    "usage_frequency": (0.0, 50.0),
    "support_calls": (0.0, 30.0),
    "payment_delay": (0.0, 90.0),
    "total_spend": (0.0, 100000.0),
    "last_interaction": (0.0, 60.0),
    "gender_encoded": (0, 1),
    "subscription_type_encoded": (0, 2),
    "contract_length_encoded": (0, 2),
    "churn": (0, 1)
}


def detect_outliers_iqr(df: pd.DataFrame, columns: list, multiplier: float = 3.0) -> dict:
    """Phát hiện giá trị ngoại lai (Extreme Outliers) theo phương pháp Interquartile Range (IQR)."""
    report = {}
    for col in columns:
        if col not in df.columns:
            continue
        vals = df[col].dropna()
        q1 = vals.quantile(0.25)
        q3 = vals.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        outliers = (vals < lower_bound) | (vals > upper_bound)
        count = int(outliers.sum())
        report[col] = {
            "method": "IQR",
            "q1": round(float(q1), 2),
            "q3": round(float(q3), 2),
            "iqr": round(float(iqr), 2),
            "lower_bound": round(float(lower_bound), 2),
            "upper_bound": round(float(upper_bound), 2),
            "outlier_count": count,
            "outlier_percentage": round(count / len(vals) * 100, 3)
        }
    return report


def detect_outliers_zscore(df: pd.DataFrame, columns: list, threshold: float = 3.5) -> dict:
    """Phát hiện giá trị dị biệt theo phân phối chuẩn Z-score (|Z| > 3.5)."""
    report = {}
    for col in columns:
        if col not in df.columns:
            continue
        vals = df[col].dropna()
        mean_val = vals.mean()
        std_val = vals.std()
        if std_val == 0:
            z_scores = np.zeros(len(vals))
        else:
            z_scores = np.abs((vals - mean_val) / std_val)

        outliers = z_scores > threshold
        count = int(outliers.sum())
        report[col] = {
            "method": "Z-score",
            "mean": round(float(mean_val), 2),
            "std": round(float(std_val), 2),
            "threshold": threshold,
            "outlier_count": count,
            "outlier_percentage": round(count / len(vals) * 100, 3)
        }
    return report


def validate_data_contracts(df: pd.DataFrame) -> dict:
    """Xác thực các ràng buộc nghiệp vụ (Data Contracts / Great Expectations Standard)."""
    checks = []

    # 1. Ràng buộc khóa chính CustomerID không trùng lặp và không rỗng
    if "customerid" in df.columns:
        null_ids = int(df["customerid"].isnull().sum())
        dup_ids = int(df["customerid"].duplicated().sum())
        checks.append({
            "expectation": "expect_column_values_to_not_be_null",
            "column": "customerid",
            "success": null_ids == 0,
            "unexpected_count": null_ids
        })
        checks.append({
            "expectation": "expect_column_values_to_be_unique",
            "column": "customerid",
            "success": dup_ids == 0,
            "unexpected_count": dup_ids
        })

    # 2. Ràng buộc miền giá trị các cột đặc trưng
    for col, (min_val, max_val) in FEATURE_BOUNDS.items():
        if col in df.columns:
            vals = df[col].dropna()
            violations = int(((vals < min_val) | (vals > max_val)).sum())
            checks.append({
                "expectation": "expect_column_values_to_be_between",
                "column": col,
                "min_value": min_val,
                "max_value": max_val,
                "success": violations == 0,
                "unexpected_count": violations
            })

    # 3. Ràng buộc tỷ lệ rò rỉ hoặc phi lý
    if "spend_per_tenure" in df.columns:
        inf_spends = int(np.isinf(df["spend_per_tenure"]).sum())
        checks.append({
            "expectation": "expect_column_values_to_be_finite",
            "column": "spend_per_tenure",
            "success": inf_spends == 0,
            "unexpected_count": inf_spends
        })

    passed_checks = sum(1 for c in checks if c["success"])
    return {
        "total_checks": len(checks),
        "passed_checks": passed_checks,
        "success_rate": round(passed_checks / max(len(checks), 1) * 100, 2),
        "checks": checks
    }


def run_data_quality_audit(parquet_path: str = TRAIN_PARQUET) -> dict:
    """Thực thi kiểm toán toàn diện chất lượng dữ liệu và xuất báo cáo JSON."""
    if not os.path.exists(parquet_path):
        print(f"[-] Lỗi: Không tìm thấy tệp {parquet_path}")
        return {}

    print(f"[*] Đang thực hiện kiểm toán chất lượng dữ liệu trên: {parquet_path}")
    df = pd.read_parquet(parquet_path)

    iqr_report = detect_outliers_iqr(df, NUMERIC_COLS, multiplier=3.0)
    zscore_report = detect_outliers_zscore(df, NUMERIC_COLS, threshold=3.5)
    contract_report = validate_data_contracts(df)

    audit_summary = {
        "dataset_file": os.path.basename(parquet_path),
        "total_records": len(df),
        "total_columns": len(df.columns),
        "outlier_analysis": {
            "iqr_method": iqr_report,
            "zscore_method": zscore_report
        },
        "data_contract_validation": contract_report,
        "overall_quality_status": "EXCELLENT" if contract_report["success_rate"] >= 95.0 else "WARNING"
    }

    os.makedirs(os.path.dirname(OUTPUT_QUALITY_JSON), exist_ok=True)
    with open(OUTPUT_QUALITY_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2, ensure_ascii=False)

    print(f"[+] Báo cáo Data Quality đã được xuất tại: {OUTPUT_QUALITY_JSON}")
    print(f"    - Tỷ lệ vượt qua kiểm định hợp đồng: {contract_report['success_rate']}%")
    print(f"    - Trạng thái chất lượng tổng thể: {audit_summary['overall_quality_status']}")
    return audit_summary


if __name__ == "__main__":
    run_data_quality_audit()
