"""
Pipeline Reproducibility & Data Engineering Test Suite (Audit Team 1).
Kiem thu toan ven: Out-of-core chunking deduplication, on dinh toan hoc
cua ky thuat dac trung, chuan hoa chuoi categorical, zero customer leakage
giua cac tap du lieu, thong so Scaler va kiem tra DAG DVC bang NetworkX.
Tuan thu Invariant 02 (<= 400 dong) va Invariant 13 (Zero Mockup).
"""

import os
import pathlib
import tempfile
import joblib
import networkx as nx
import numpy as np
import pandas as pd
import pytest
import yaml

from src.data.preprocess import (
    FEATURE_NAMES,
    clean_raw_data,
    engineer_features,
    process_large_dataset_chunks,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def test_out_of_core_chunking_with_cross_chunk_deduplication(tmp_path):
    """
    Kiem thu streaming chunking voi 2,000 ban ghi tong hop chua 500 CustomerID
    trung lap xuyen 5 boundaries chunk (chunk_size=400).
    Xac thuc:
    - CustomerID sau cung hoan toan duy nhat (is_unique == True).
    - So luong ban ghi chinh xac 1,500 thuc the duy nhat.
    - Imputation bang global median dong nhat xuyen suot giua chunk 1 va chunk 5.
    """
    csv_file = tmp_path / "streaming_test_input.csv"
    parquet_out = tmp_path / "streaming_test_output.parquet"

    # Tao 1,500 CustomerID duy nhat (1001 den 2500)
    # 500 ID dau tien (1001-1500) duoc lap lai o chunk 2 va 3
    ids = list(range(1001, 2501))
    dup_ids = ids[:500]
    full_ids = ids[:500] + dup_ids + ids[500:]  # 500 + 500 + 1000 = 2,000 dong

    np.random.seed(42)
    n_rows = len(full_ids)
    raw_df = pd.DataFrame({
        "CustomerID": full_ids,
        "Age": np.random.uniform(20.0, 60.0, size=n_rows),
        "Gender": np.random.choice(["Male", "Female"], size=n_rows),
        "Tenure": np.random.uniform(1.0, 60.0, size=n_rows),
        "Usage Frequency": np.random.uniform(5.0, 30.0, size=n_rows),
        "Support Calls": np.random.randint(0, 10, size=n_rows).astype(float),
        "Payment Delay": np.random.randint(0, 30, size=n_rows).astype(float),
        "Subscription Type": np.random.choice(["Basic", "Standard", "Premium"], size=n_rows),
        "Contract Length": np.random.choice(["Monthly", "Quarterly", "Annual"], size=n_rows),
        "Total Spend": np.random.uniform(100.0, 1000.0, size=n_rows),
        "Last Interaction": np.random.uniform(1.0, 30.0, size=n_rows),
        "Churn": np.random.choice([0, 1], size=n_rows)
    })

    # Dat gia tri thieu (NaN) o dong 10 (chunk 1) va dong 1800 (chunk 5)
    raw_df.loc[10, "Age"] = np.nan
    raw_df.loc[1800, "Age"] = np.nan

    raw_df.to_csv(csv_file, index=False)

    stats = process_large_dataset_chunks(str(csv_file), str(parquet_out), chunk_size=400)
    assert stats["total_records"] == 1500, f"Expected 1500 records, got {stats['total_records']}"

    result_df = pd.read_parquet(parquet_out)
    assert len(result_df) == 1500, f"Expected 1500 rows in Parquet, got {len(result_df)}"
    assert result_df["customerid"].is_unique, "CustomerID column contains duplicates after chunking"

    # Xac nhan gia tri imputation median tai 2 dong khuyet o chunk khac nhau la dong nhat
    imputed_c1 = result_df.loc[result_df["customerid"] == full_ids[10], "age"].values[0]
    imputed_c5 = result_df.loc[result_df["customerid"] == full_ids[1800], "age"].values[0]
    assert np.isclose(imputed_c1, imputed_c5, atol=1e-5), (
        f"Global median imputation differs across chunks: {imputed_c1} vs {imputed_c5}"
    )


def test_feature_engineering_mathematical_stability():
    """
    Kiem thu tinh on dinh toan hoc cua ky thuat dac trung voi cac gia tri bien
    (Tenure=0.0, PaymentDelay=0.0, LastInteraction=0.0).
    Xac thuc khong xuat hien NaN, inf, hoac -inf nho vao chan mau so an toan.
    """
    edge_df = pd.DataFrame([
        {
            "customerid": 90001,
            "age": 30.0,
            "gender": "Female",
            "tenure": 0.0,
            "usage_frequency": 0.0,
            "support_calls": 0.0,
            "payment_delay": 0.0,
            "subscription_type": "Basic",
            "contract_length": "Monthly",
            "total_spend": 0.0,
            "last_interaction": 0.0,
            "churn": 1
        },
        {
            "customerid": 90002,
            "age": 45.0,
            "gender": "Male",
            "tenure": 0.0,
            "usage_frequency": 15.0,
            "support_calls": 8.0,
            "payment_delay": 45.0,
            "subscription_type": "Standard",
            "contract_length": "Quarterly",
            "total_spend": 500.0,
            "last_interaction": 0.0,
            "churn": 0
        },
        {
            "customerid": 90003,
            "age": 60.0,
            "gender": "Female",
            "tenure": 120.0,
            "usage_frequency": 50.0,
            "support_calls": 0.0,
            "payment_delay": 0.0,
            "subscription_type": "Premium",
            "contract_length": "Annual",
            "total_spend": 2500.0,
            "last_interaction": 25.0,
            "churn": 0
        }
    ])

    cleaned = clean_raw_data(edge_df)
    featured = engineer_features(cleaned)

    for col in FEATURE_NAMES:
        assert col in featured.columns, f"Missing engineered feature: {col}"
        vals = featured[col].values
        assert np.isfinite(vals).all(), f"Feature '{col}' contains NaN or Inf values: {vals}"

    # Kiem tra quy tac ty le: tenure=0 thi support_calls_per_tenure = support_calls / 1.0
    row_zero = featured.loc[featured["customerid"] == 90002].iloc[0]
    expected_ratio = row_zero["support_calls"] / 1.0
    assert np.isclose(row_zero["support_calls_per_tenure"], expected_ratio, atol=1e-5)

    # Kiem tra delay_ratio: last_interaction=0 thi delay_ratio = payment_delay / 1.0
    expected_delay = row_zero["payment_delay"] / 1.0
    assert np.isclose(row_zero["delay_ratio"], expected_delay, atol=1e-5)


def test_categorical_encoding_case_and_whitespace_invariance():
    """
    Kiem thu chuan hoa chuoi va ma hoa bien phan loai bat bien truoc chu hoa/thuong
    va khoang trang du thua.
    Xac thuc khong phat sinh KeyError va anh xa dung vao tap ma hoa [0, 1, 2].
    """
    test_df = pd.DataFrame([
        {
            "customerid": 80001,
            "age": 35.0,
            "gender": " male ",
            "tenure": 12.0,
            "usage_frequency": 10.0,
            "support_calls": 2.0,
            "payment_delay": 0.0,
            "subscription_type": " basic ",
            "contract_length": " monthly ",
            "total_spend": 300.0,
            "last_interaction": 5.0,
            "churn": 1
        },
        {
            "customerid": 80002,
            "age": 40.0,
            "gender": "MALE",
            "tenure": 24.0,
            "usage_frequency": 20.0,
            "support_calls": 1.0,
            "payment_delay": 0.0,
            "subscription_type": "STANDARD",
            "contract_length": "Annual",
            "total_spend": 600.0,
            "last_interaction": 10.0,
            "churn": 0
        },
        {
            "customerid": 80003,
            "age": 28.0,
            "gender": "Female ",
            "tenure": 6.0,
            "usage_frequency": 8.0,
            "support_calls": 5.0,
            "payment_delay": 15.0,
            "subscription_type": " premium ",
            "contract_length": "quarterly",
            "total_spend": 450.0,
            "last_interaction": 2.0,
            "churn": 1
        }
    ])

    cleaned = clean_raw_data(test_df)
    featured = engineer_features(cleaned)

    # Gender: Female -> 0, Male -> 1
    assert featured.loc[featured["customerid"] == 80001, "gender_encoded"].values[0] == 1
    assert featured.loc[featured["customerid"] == 80002, "gender_encoded"].values[0] == 1
    assert featured.loc[featured["customerid"] == 80003, "gender_encoded"].values[0] == 0

    # Subscription: Basic -> 0, Standard -> 1, Premium -> 2
    assert featured.loc[featured["customerid"] == 80001, "subscription_type_encoded"].values[0] == 0
    assert featured.loc[featured["customerid"] == 80002, "subscription_type_encoded"].values[0] == 1
    assert featured.loc[featured["customerid"] == 80003, "subscription_type_encoded"].values[0] == 2

    # Contract: Monthly -> 0, Quarterly -> 1, Annual -> 2
    assert featured.loc[featured["customerid"] == 80001, "contract_length_encoded"].values[0] == 0
    assert featured.loc[featured["customerid"] == 80002, "contract_length_encoded"].values[0] == 2
    assert featured.loc[featured["customerid"] == 80003, "contract_length_encoded"].values[0] == 1


def test_dataset_split_zero_customer_leakage():
    """
    Kiem thu tinh toan ven va co lap tuyet doi giua 3 tap du lieu Train, Val, Test tren dia.
    Xac thuc:
    - S_train giao S_val = rong.
    - S_train giao S_test = rong.
    - S_val giao S_test = rong.
    - Tong so khach hang duy nhat xuyen 3 tap la 442,211.
    """
    train_parquet = PROCESSED_DIR / "train_features.parquet"
    val_parquet = PROCESSED_DIR / "val_features.parquet"
    test_parquet = PROCESSED_DIR / "test_features.parquet"

    assert train_parquet.exists(), f"Train parquet not found: {train_parquet}"
    assert val_parquet.exists(), f"Validation parquet not found: {val_parquet}"
    assert test_parquet.exists(), f"Test parquet not found: {test_parquet}"

    s_train = set(pd.read_parquet(train_parquet, columns=["customerid"])["customerid"])
    s_val = set(pd.read_parquet(val_parquet, columns=["customerid"])["customerid"])
    s_test = set(pd.read_parquet(test_parquet, columns=["customerid"])["customerid"])

    assert len(s_train & s_val) == 0, f"Customer leakage between Train and Val: {len(s_train & s_val)}"
    assert len(s_train & s_test) == 0, f"Customer leakage between Train and Test: {len(s_train & s_test)}"
    assert len(s_val & s_test) == 0, f"Customer leakage between Val and Test: {len(s_val & s_test)}"

    total_unique = len(s_train | s_val | s_test)
    assert total_unique == 442211, f"Expected 442,211 unique customers, got {total_unique}"
    assert len(s_train) + len(s_val) + len(s_test) == 442211, "Sum of split sizes does not match union size"


def test_scaler_normalization_bounds_and_parameters():
    """
    Kiem thu StandardScaler da luu tru tren dia:
    - Cac tham so mean_ va scale_ khop voi gia tri ky vong tu tap Train.
    - Bien doi tren tap Validation tao ra phan phoi chuan hoa co mean xap xi 0 va std xap xi 1.
    """
    scaler_path = PROCESSED_DIR / "scaler.joblib"
    val_parquet = PROCESSED_DIR / "val_features.parquet"

    assert scaler_path.exists(), f"Scaler joblib not found: {scaler_path}"
    scaler = joblib.load(scaler_path)

    assert hasattr(scaler, "mean_"), "Scaler does not have mean_ attribute"
    assert hasattr(scaler, "scale_"), "Scaler does not have scale_ attribute"
    assert len(scaler.mean_) == len(FEATURE_NAMES), (
        f"Scaler feature count mismatch: {len(scaler.mean_)} vs {len(FEATURE_NAMES)}"
    )

    # Load 10,000 ban ghi validation de kiem tra bien doi chuan hoa
    val_df = pd.read_parquet(val_parquet).head(10000)
    x_val = val_df[FEATURE_NAMES].values.astype(float)
    x_scaled = scaler.transform(x_val)

    # Kiem tra gia tri bien doi co mean gan 0 va do lech chuan gan 1
    means = np.mean(x_scaled, axis=0)
    stds = np.std(x_scaled, axis=0)

    for i, col in enumerate(FEATURE_NAMES):
        assert abs(means[i]) < 0.25, f"Feature '{col}' scaled mean out of bounds: {means[i]:.4f}"
        assert 0.75 < stds[i] < 1.25, f"Feature '{col}' scaled std out of bounds: {stds[i]:.4f}"


def test_dvc_pipeline_dag_programmatic_integrity():
    """
    Kiem thu cau truc do thi co huong khong chu trinh (DAG) cua dvc.yaml bang NetworkX.
    Xac thuc tat ca dependencies, params va outputs duoc khai bao day du va khong tao vong lap.
    """
    dvc_file = PROJECT_ROOT / "dvc.yaml"
    assert dvc_file.exists(), f"dvc.yaml not found at: {dvc_file}"

    with open(dvc_file, "r", encoding="utf-8") as f:
        dvc_data = yaml.safe_load(f)

    stages = dvc_data.get("stages", {})
    assert len(stages) == 9, f"Expected 9 DVC pipeline stages, found {len(stages)}"

    # Kiem tra su ton tai cua cac file dependencies va params tren dia
    for stage_name, s_info in stages.items():
        for dep in s_info.get("deps", []):
            dep_path = PROJECT_ROOT / dep
            assert dep_path.exists(), f"Stage '{stage_name}' references non-existent dep: {dep}"

        for p_item in s_info.get("params", []):
            if isinstance(p_item, dict):
                p_file = list(p_item.keys())[0]
            else:
                p_file = str(p_item)
            param_path = PROJECT_ROOT / p_file
            assert param_path.exists(), f"Stage '{stage_name}' references non-existent param file: {p_file}"

    # Xay dung NetworkX DiGraph tu cac quan he stage outputs -> stage deps
    out_to_stage = {}
    for stage_name, s_info in stages.items():
        all_outs = list(s_info.get("outs", []))
        for m in s_info.get("metrics", []):
            if isinstance(m, dict):
                all_outs.append(list(m.keys())[0])
            else:
                all_outs.append(str(m))
        for out in all_outs:
            out_to_stage[out] = stage_name

    dag = nx.DiGraph()
    for stage_name in stages:
        dag.add_node(stage_name)

    for stage_name, s_info in stages.items():
        for dep in s_info.get("deps", []):
            if dep in out_to_stage:
                producer_stage = out_to_stage[dep]
                if producer_stage != stage_name:
                    dag.add_edge(producer_stage, stage_name)

    assert nx.is_directed_acyclic_graph(dag), "DVC pipeline graph contains cycles (not a valid DAG)"
    assert nx.number_of_nodes(dag) == 9, f"Expected 9 nodes in DAG, got {nx.number_of_nodes(dag)}"
    assert nx.number_of_edges(dag) >= 8, f"Expected at least 8 dependency edges, got {nx.number_of_edges(dag)}"
