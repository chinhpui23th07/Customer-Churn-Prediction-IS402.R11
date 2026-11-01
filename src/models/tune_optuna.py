"""
Module tối ưu hóa siêu tham số bằng Optuna (Bayesian Optimization với TPE Sampler).
Tìm kiếm cấu hình tối ưu cho Champion XGBoost và Challenger Random Forest.
"""
import os
import sys
import json
import joblib
import optuna
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import StratifiedKFold, cross_val_score
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier

# Tắt logging ồn ào của Optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
IMAGES_DIR = os.path.join(BASE_DIR, "docs", "images")
TUNING_FILE = os.path.join(MODELS_DIR, "tuning_history.json")

FEATURE_COLS = [
    "age", "gender_encoded", "tenure", "usage_frequency", "support_calls",
    "payment_delay", "subscription_type_encoded", "contract_length_encoded",
    "total_spend", "last_interaction", "support_calls_per_tenure",
    "spend_per_tenure", "delay_ratio"
]


def load_tuning_subset(n_samples: int = 25000):
    """Nạp tập mẫu đại diện phục vụ tối ưu hóa Bayes tốc độ cao."""
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "train_features.parquet"))
    sample_df = train_df.sample(n=min(len(train_df), n_samples), random_state=42)
    return sample_df[FEATURE_COLS], sample_df["churn"]


def run_optuna_tuning(n_trials: int = 12):
    """Thực thi Bayesian Optimization với Optuna Tree-structured Parzen Estimator (TPE)."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    X, y = load_tuning_subset(n_samples=25000)
    skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

    print(f"[*] Khởi động Optuna Bayesian Optimization ({n_trials} trials, 3-Fold Stratified CV)...")

    # 1. Tối ưu hóa XGBoost (Champion)
    def objective_xgb(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 80, 160, step=20),
            "max_depth": trial.suggest_int("max_depth", 4, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.04, 0.12, log=True),
            "subsample": trial.suggest_float("subsample", 0.7, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.7, 0.95),
            "random_state": 42,
            "n_jobs": -1
        }
        clf = xgb.XGBClassifier(**params)
        scores = cross_val_score(clf, X, y, cv=skf, scoring="roc_auc", n_jobs=-1)
        return float(np.mean(scores))

    study_xgb = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study_xgb.optimize(objective_xgb, n_trials=n_trials)

    print(f"[+] XGBoost Best Trial #{study_xgb.best_trial.number}: ROC-AUC = {study_xgb.best_value:.4f}")
    print(f"    Best Parameters: {study_xgb.best_params}")

    # 2. Tối ưu hóa Random Forest (Challenger)
    def objective_rf(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 60, 120, step=20),
            "max_depth": trial.suggest_int("max_depth", 8, 14),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 6),
            "random_state": 42,
            "n_jobs": -1
        }
        clf = RandomForestClassifier(**params)
        scores = cross_val_score(clf, X, y, cv=skf, scoring="roc_auc", n_jobs=-1)
        return float(np.mean(scores))

    study_rf = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study_rf.optimize(objective_rf, n_trials=min(n_trials, 8))

    print(f"[+] Random Forest Best Trial #{study_rf.best_trial.number}: ROC-AUC = {study_rf.best_value:.4f}")
    print(f"    Best Parameters: {study_rf.best_params}")

    # Xuất lịch sử trials vào JSON
    xgb_trials_data = [
        {"trial_id": t.number, "value": round(float(t.value), 4), "params": t.params}
        for t in study_xgb.trials
    ]
    rf_trials_data = [
        {"trial_id": t.number, "value": round(float(t.value), 4), "params": t.params}
        for t in study_rf.trials
    ]

    tuning_summary = {
        "framework": "Optuna 4.8.0 + Bayesian TPE Sampler",
        "objective": "Maximize 3-Fold Stratified Cross-Validation ROC-AUC",
        "sample_size": len(X),
        "xgboost_champion": {
            "best_roc_auc": round(float(study_xgb.best_value), 4),
            "best_params": study_xgb.best_params,
            "trials_count": len(study_xgb.trials),
            "trials_history": xgb_trials_data
        },
        "random_forest_challenger": {
            "best_roc_auc": round(float(study_rf.best_value), 4),
            "best_params": study_rf.best_params,
            "trials_count": len(study_rf.trials),
            "trials_history": rf_trials_data
        }
    }

    with open(TUNING_FILE, "w", encoding="utf-8") as f:
        json.dump(tuning_summary, f, indent=2, ensure_ascii=False)
    print(f"[+] Đã lưu lịch sử Optuna Tuning vào: {TUNING_FILE}")

    # Vẽ biểu đồ tiến trình tối ưu hóa
    plt.figure(figsize=(10, 5))
    xgb_vals = [t.value for t in study_xgb.trials]
    rf_vals = [t.value for t in study_rf.trials]
    plt.plot(range(1, len(xgb_vals) + 1), xgb_vals, marker="o", color="#00D4B2", linewidth=2.2, label="Champion XGBoost")
    plt.plot(range(1, len(rf_vals) + 1), rf_vals, marker="s", color="#FFB703", linewidth=2.0, linestyle="--", label="Challenger Random Forest")
    plt.axhline(y=study_xgb.best_value, color="#0A2540", linestyle=":", label=f"XGB Best ({study_xgb.best_value:.4f})")
    plt.title("Tiến Trình Tối Ưu Hóa Siêu Tham Số Bằng Optuna (Bayesian TPE Sampler)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Thử Nghiệm (Trial Number)", fontsize=11)
    plt.ylabel("3-Fold CV ROC-AUC", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(frameon=True)
    plt.tight_layout()

    out_img = os.path.join(IMAGES_DIR, "optuna_optimization.png")
    plt.savefig(out_img, dpi=300)
    plt.close()
    print(f"[+] Đã lưu biểu đồ Optuna Optimization vào: {out_img}")
    return tuning_summary


if __name__ == "__main__":
    run_optuna_tuning(n_trials=12)
