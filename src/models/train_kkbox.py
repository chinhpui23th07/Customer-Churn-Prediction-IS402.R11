"""
Pipeline huan luyen mo hinh KKBox Churn Prediction tren tap du lieu thuc te.
Tich hop LightGBM / HistGradientBoosting voi xac suat lien tuc va phan bo rui ro chuan hoa.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
import lightgbm as lgb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "real_hf_kkbox_full_window.parquet")
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "data", "models", "kkbox_champion_model.joblib")
DEFAULT_METRICS_PATH = os.path.join(BASE_DIR, "data", "models", "kkbox_evaluation_results.json")

KKBOX_BEHAVIORAL_FEATURES: List[str] = [
    "city",
    "bd",
    "gender_encoded",
    "registered_via",
    "trans_count",
    "avg_plan_days",
    "total_actual_paid",
    "auto_renew_ratio",
    "cancel_ratio",
    "discount_ratio",
    "listen_days_count",
    "total_listen_secs",
    "total_songs_played",
    "completion_ratio",
    "unique_song_ratio",
]

TARGET_COL: str = "is_churn"
ID_COL: str = "msno"


def load_kkbox_dataset(
    parquet_path: Optional[str] = None,
    sample_size: Optional[int] = None,
    test_size: float = 0.2,
    random_state: int = 42,
    split_mode: str = "temporal",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, List[str], Dict[str, Any]]:
    """
    Nap tap du lieu KKBox thuc te tu tep Parquet, xu ly ep kieu DuckDB decimal128 sang float64.
    Uu tien Out-of-Time split khi tap du lieu co tu 2 cua so thoi gian tro len; ghi ro chien luoc
    split_strategy vao metadata de dam bao minh bach hoc thuat.
    """
    path = parquet_path or DEFAULT_DATA_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Khong tim thay tap du lieu KKBox tai: {path}")

    df = pd.read_parquet(path)

    # Xu ly kieu du lieu DuckDB decimal128 cho cot total_actual_paid
    if "total_actual_paid" in df.columns:
        df["total_actual_paid"] = df["total_actual_paid"].astype(float)

    total_rows = len(df)
    churn_rate = float(df[TARGET_COL].mean())

    if sample_size and sample_size < total_rows:
        df = df.sample(n=sample_size, random_state=random_state).reset_index(drop=True)

    missing_cols = [c for c in KKBOX_BEHAVIORAL_FEATURES if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Thieu cac cot dac trung bat buoc: {missing_cols}")

    time_col = "as_of_date" if "as_of_date" in df.columns else ("label_period" if "label_period" in df.columns else None)
    distinct_windows = sorted(df[time_col].astype(str).unique().tolist()) if time_col else []

    if split_mode == "temporal" and len(distinct_windows) >= 2:
        holdout_window = distinct_windows[-1]
        train_mask = df[time_col].astype(str) != holdout_window
        test_mask = df[time_col].astype(str) == holdout_window
        X_train = df.loc[train_mask, KKBOX_BEHAVIORAL_FEATURES].copy()
        X_test = df.loc[test_mask, KKBOX_BEHAVIORAL_FEATURES].copy()
        y_train = df.loc[train_mask, TARGET_COL].astype(int).copy()
        y_test = df.loc[test_mask, TARGET_COL].astype(int).copy()
        split_strategy = f"temporal_out_of_time ({distinct_windows[0]} -> {holdout_window})"
    else:
        X = df[KKBOX_BEHAVIORAL_FEATURES].copy()
        y = df[TARGET_COL].astype(int).copy()
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        split_strategy = "stratified_single_window_comparative_benchmark"

    metadata = {
        "source_path": path,
        "total_source_rows": total_rows,
        "loaded_rows": len(df),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "overall_churn_rate": churn_rate,
        "feature_count": len(KKBOX_BEHAVIORAL_FEATURES),
        "split_strategy": split_strategy,
    }

    return X_train, X_test, y_train, y_test, KKBOX_BEHAVIORAL_FEATURES, metadata


def evaluate_kkbox_predictions(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Danh gia chi tiet hieu nang du doan va phan tich phan bo xac suat rui ro.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_probs_arr = np.asarray(y_probs, dtype=float)
    y_pred_arr = (y_probs_arr >= threshold).astype(int)

    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    prec = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))
    roc_auc = float(roc_auc_score(y_true_arr, y_probs_arr))
    pr_auc = float(average_precision_score(y_true_arr, y_probs_arr))
    brier = float(brier_score_loss(y_true_arr, y_probs_arr))
    cm = confusion_matrix(y_true_arr, y_pred_arr).tolist()

    total_n = len(y_probs_arr)
    low_mask = y_probs_arr < 0.40
    mid_mask = (y_probs_arr >= 0.40) & (y_probs_arr < 0.70)
    high_mask = y_probs_arr >= 0.70

    prob_dist = {
        "p_min": float(np.min(y_probs_arr)),
        "p_max": float(np.max(y_probs_arr)),
        "p_mean": float(np.mean(y_probs_arr)),
        "p_median": float(np.median(y_probs_arr)),
        "low_risk_ratio": float(np.mean(low_mask)),
        "mid_risk_ratio": float(np.mean(mid_mask)),
        "high_risk_ratio": float(np.mean(high_mask)),
        "mid_risk_count": int(np.sum(mid_mask)),
        "total_evaluated": total_n,
    }

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 5),
        "confusion_matrix": cm,
        "probability_distribution": prob_dist,
    }


def create_model_estimator(
    model_type: str = "lgbm",
    random_state: int = 42,
    n_estimators: int = 100,
) -> Any:
    """Khoi tao mo hinh phan loai gradient boosting ho tro Missing Values."""
    m_type = model_type.lower()
    if m_type == "lgbm":
        return lgb.LGBMClassifier(
            n_estimators=n_estimators,
            learning_rate=0.08,
            num_leaves=31,
            max_depth=6,
            min_child_samples=50,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        )
    elif m_type == "hgb":
        return HistGradientBoostingClassifier(
            max_iter=n_estimators,
            learning_rate=0.08,
            max_leaf_nodes=31,
            max_depth=6,
            min_samples_leaf=50,
            random_state=random_state,
        )
    else:
        raise ValueError(f"Loai mo hinh khong ho tro: {model_type}. Chi ho tro 'lgbm' hoac 'hgb'.")


def train_kkbox_champion(
    parquet_path: Optional[str] = None,
    sample_size: Optional[int] = None,
    model_type: str = "lgbm",
    cv_folds: int = 5,
    random_state: int = 42,
    save_path: Optional[str] = None,
    metrics_path: Optional[str] = None,
    split_mode: str = "temporal",
) -> Dict[str, Any]:
    """
    Huan luyen mo hinh Champion KKBox, danh gia 5-Fold CV va luu model bundle.
    """
    t_start = time.perf_counter()
    X_train, X_test, y_train, y_test, feature_names, meta = load_kkbox_dataset(
        parquet_path=parquet_path,
        sample_size=sample_size,
        random_state=random_state,
        split_mode=split_mode,
    )

    clf = create_model_estimator(model_type=model_type, random_state=random_state)

    # 1. Cross-validation tren tap train
    cv_results = {}
    if cv_folds and cv_folds > 1:
        cv_splitter = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
        scores = cross_val_score(clf, X_train, y_train, cv=cv_splitter, scoring="roc_auc", n_jobs=-1)
        cv_results = {
            "folds": cv_folds,
            "roc_auc_mean": round(float(np.mean(scores)), 4),
            "roc_auc_std": round(float(np.std(scores)), 4),
            "fold_scores": [round(float(s), 4) for s in scores],
        }

    # 2. Huan luyen toan bo tren tap train
    clf.fit(X_train, y_train)

    # 3. Danh gia tren tap test held-out
    y_probs = clf.predict_proba(X_test)[:, 1]
    test_metrics = evaluate_kkbox_predictions(y_test.values, y_probs)

    # 4. Trinh trich xuat do quan trong dac trung
    feat_importances = {}
    if hasattr(clf, "feature_importances_"):
        imps = np.asarray(clf.feature_importances_, dtype=float)
        if np.sum(imps) > 0:
            imps = imps / np.sum(imps)
        feat_importances = {fn: round(float(imps[i]), 4) for i, fn in enumerate(feature_names)}

    duration = round(time.perf_counter() - t_start, 2)

    # 5. Dong goi Champion Model Bundle
    bundle = {
        "name": f"KKBox_{model_type.upper()}_Champion",
        "model_type": model_type,
        "model": clf,
        "feature_names": feature_names,
        "target_col": TARGET_COL,
        "id_col": ID_COL,
        "params": clf.get_params(),
        "cv_5fold": cv_results,
        "metrics": test_metrics,
        "probability_distribution": test_metrics["probability_distribution"],
        "feature_importance": feat_importances,
        "dataset_metadata": meta,
        "train_duration_sec": duration,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }

    # 6. Luu model bundle va bao cao JSON
    out_model_path = save_path or DEFAULT_MODEL_PATH
    os.makedirs(os.path.dirname(out_model_path), exist_ok=True)
    joblib.dump(bundle, out_model_path)

    out_metrics_path = metrics_path or DEFAULT_METRICS_PATH
    summary_data = {
        "model_name": bundle["name"],
        "metrics": test_metrics,
        "cv_5fold": cv_results,
        "probability_distribution": test_metrics["probability_distribution"],
        "feature_importance": feat_importances,
        "dataset_metadata": meta,
        "train_duration_sec": duration,
        "trained_at": bundle["trained_at"],
    }
    with open(out_metrics_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    return bundle


def parse_cli_args() -> argparse.Namespace:
    """Xu ly tham so dong lenh CLI."""
    parser = argparse.ArgumentParser(description="KKBox Churn Model Training Pipeline")
    parser.add_argument("--data-path", type=str, default=DEFAULT_DATA_PATH, help="Duong dan tep Parquet KKBox")
    parser.add_argument("--save-path", type=str, default=DEFAULT_MODEL_PATH, help="Duong dan luu file joblib")
    parser.add_argument("--metrics-path", type=str, default=DEFAULT_METRICS_PATH, help="Duong dan luu metrics json")
    parser.add_argument("--model-type", type=str, default="lgbm", choices=["lgbm", "hgb"], help="Loai mo hinh")
    parser.add_argument("--sample-size", type=int, default=None, help="So luong mau toi da (ho tro CI/CD test nhanh)")
    parser.add_argument("--cv-folds", type=int, default=5, help="So fold K-Fold CV")
    parser.add_argument("--split-mode", type=str, default="temporal", choices=["temporal", "stratified"], help="Chien luoc chia train/test")
    parser.add_argument("--dry-run", action="store_true", help="Kiem tra phu thuoc va du lieu ma khong chay huan luyen")
    return parser.parse_args()


def main() -> None:
    """Diem khoi chay dong lenh CLI."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    args = parse_cli_args()

    if args.dry_run:
        print("[*] KKBox Pipeline Dry-Run: Validating dependencies and dataset...")
        if not os.path.exists(args.data_path):
            print(f"[-] Loi: Khong tim thay tep du lieu tai {args.data_path}")
            sys.exit(1)
        sample_df = pd.read_parquet(args.data_path)
        sample_df["total_actual_paid"] = sample_df["total_actual_paid"].astype(float)
        print(f"[+] Tap du lieu hop le: {len(sample_df):,} hang, {len(sample_df.columns)} cot.")
        print(f"[+] Kieu du lieu total_actual_paid da duoc ep sang float64 thanh cong.")
        print("[+] Dry-run completed successfully with exit code 0.")
        sys.exit(0)

    print(f"[*] Bat dau huan luyen KKBox Champion Model ({args.model_type.upper()})...")
    bundle = train_kkbox_champion(
        parquet_path=args.data_path,
        sample_size=args.sample_size,
        model_type=args.model_type,
        cv_folds=args.cv_folds,
        save_path=args.save_path,
        metrics_path=args.metrics_path,
        split_mode=args.split_mode,
    )

    p_dist = bundle["probability_distribution"]
    test_m = bundle["metrics"]
    cv_m = bundle["cv_5fold"]

    print("\n================== KET QUA HUAN LUYEN KKBOX CHAMPION ==================")
    print(f"Model: {bundle['name']}")
    print(f"Thoi gian huan luyen: {bundle['train_duration_sec']} giay")
    if cv_m:
        print(f"5-Fold CV ROC-AUC: {cv_m['roc_auc_mean']:.4f} +- {cv_m['roc_auc_std']:.4f}")
    print(f"Test ROC-AUC: {test_m['roc_auc']:.4f} | PR-AUC: {test_m['pr_auc']:.4f} | F1: {test_m['f1_score']:.4f}")
    print(f"Phan bo xac suat: Min={p_dist['p_min']:.4f}, Mean={p_dist['p_mean']:.4f}, Max={p_dist['p_max']:.4f}")
    print(f"Ty le Mid-Risk [0.40, 0.70): {p_dist['mid_risk_ratio'] * 100:.2f}% ({p_dist['mid_risk_count']:,} khach hang)")
    print(f"[+] Model da duoc luu tai: {args.save_path}")
    print("=======================================================================")


if __name__ == "__main__":
    main()
