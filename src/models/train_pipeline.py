"""
Module huấn luyện đa mô hình học máy (Logistic Regression, Random Forest, XGBoost, LightGBM)
kết hợp MLflow tracking và Model Registry.
Tuân thủ Invariant 01 (Clean Architecture) và Invariant 02 (< 400 dòng).
"""
import os
import sys
import time
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix, roc_curve
)
import mlflow
import mlflow.sklearn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
MLFLOW_DB = os.path.join(BASE_DIR, "data", "mlflow.db")

FEATURE_COLS = [
    "age", "gender_encoded", "tenure", "usage_frequency", "support_calls",
    "payment_delay", "subscription_type_encoded", "contract_length_encoded",
    "total_spend", "last_interaction", "support_calls_per_tenure",
    "spend_per_tenure", "delay_ratio"
]


def load_training_data(max_train_samples: int = None):
    """Nạp dữ liệu huấn luyện và kiểm định từ Parquet."""
    train_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "train_features.parquet"))
    val_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "val_features.parquet"))
    test_df = pd.read_parquet(os.path.join(PROCESSED_DIR, "test_features.parquet"))

    if max_train_samples and len(train_df) > max_train_samples:
        train_df = train_df.iloc[:max_train_samples]

    print(f"[*] Nạp dữ liệu Parquet từ: {PROCESSED_DIR}")
    print(f"    - Tập huấn luyện (Train): {len(train_df):,} mẫu (100% dữ liệu train)")
    print(f"    - Tập kiểm định (Val):   {len(val_df):,} mẫu")
    print(f"    - Tập kiểm thử (Test):   {len(test_df):,} mẫu")
    print(f"    - Không gian đặc trưng:  {len(FEATURE_COLS)} đặc trưng hành vi")

    X_train = train_df[FEATURE_COLS]
    y_train = train_df["churn"]
    X_val = val_df[FEATURE_COLS]
    y_val = val_df["churn"]
    X_test = test_df[FEATURE_COLS]
    y_test = test_df["churn"]

    scaler = joblib.load(os.path.join(PROCESSED_DIR, "scaler.joblib"))
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    return (X_train, X_train_scaled, y_train), (X_val, X_val_scaled, y_val), (X_test, X_test_scaled, y_test)


def evaluate_model_performance(model, X_raw, X_scaled, y_true, is_linear: bool = False):
    """Tính toán toàn diện các chỉ số đánh giá mô hình."""
    X_eval = X_scaled if is_linear else X_raw
    t0 = time.perf_counter()
    y_pred = model.predict(X_eval)
    inf_time_ms = (time.perf_counter() - t0) * 1000.0 / len(y_true)

    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_eval)[:, 1]
    else:
        y_prob = y_pred

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)
    cm = confusion_matrix(y_true, y_pred).tolist()

    fpr, tpr, _ = roc_curve(y_true, y_prob)
    # Lấy mẫu 20 điểm trên ROC curve để serialize JSON nhẹ nhàng
    step = max(len(fpr) // 20, 1)
    roc_points = [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in range(0, len(fpr), step)]

    return {
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "latency_per_sample_ms": round(float(inf_time_ms), 4),
        "confusion_matrix": cm,
        "roc_curve": roc_points
    }


def train_and_track_all_models():
    """Quy trình huấn luyện và ghi nhận thí nghiệm với MLflow."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    sqlite_uri = f"sqlite:///{MLFLOW_DB.replace('\\', '/')}"
    mlflow.set_tracking_uri(sqlite_uri)
    mlflow.set_experiment("Customer_Churn_Prediction_Enterprise")

    (X_train, X_train_scaled, y_train), (X_val, X_val_scaled, y_val), (X_test, X_test_scaled, y_test) = load_training_data()

    models_config = [
        {
            "name": "Logistic_Regression",
            "type": "linear",
            "model": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            "use_scaled": True,
            "params": {"penalty": "l2", "solver": "lbfgs", "class_weight": "balanced"}
        },
        {
            "name": "Random_Forest",
            "type": "ensemble",
            "model": RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1),
            "use_scaled": False,
            "params": {"n_estimators": 100, "max_depth": 12, "criterion": "gini"}
        },
        {
            "name": "XGBoost",
            "type": "gradient_boosting",
            "model": xgb.XGBClassifier(
                n_estimators=120, max_depth=6, learning_rate=0.08,
                subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1
            ),
            "use_scaled": False,
            "params": {"n_estimators": 120, "max_depth": 6, "learning_rate": 0.08}
        },
        {
            "name": "LightGBM",
            "type": "gradient_boosting",
            "model": lgb.LGBMClassifier(
                n_estimators=120, max_depth=6, learning_rate=0.08,
                num_leaves=31, random_state=42, n_jobs=-1, verbose=-1
            ),
            "use_scaled": False,
            "params": {"n_estimators": 120, "max_depth": 6, "num_leaves": 31}
        }
    ]

    all_results = {}
    best_model_name = None
    best_roc_auc = -1.0
    best_model_obj = None
    best_is_scaled = False

    print("\n[*] Bắt đầu huấn luyện và so sánh 4 mô hình Machine Learning...")

    for cfg in models_config:
        name = cfg["name"]
        print(f"\n---> Huấn luyện mô hình: {name}")
        clf = cfg["model"]
        use_scaled = cfg["use_scaled"]
        print(f"    [*] Tham số cấu hình: {cfg['params']}")
        print(f"    [*] Bắt đầu huấn luyện trên {len(X_train):,} mẫu dữ liệu...")

        with mlflow.start_run(run_name=name):
            mlflow.log_params(cfg["params"])

            t_start = time.perf_counter()
            if name == "XGBoost":
                clf.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=50)
            elif name == "LightGBM":
                clf.fit(X_train, y_train, eval_set=[(X_val, y_val)], callbacks=[lgb.log_evaluation(period=50)])
            elif use_scaled:
                clf.fit(X_train_scaled, y_train)
            else:
                clf.fit(X_train, y_train)
            train_duration = time.perf_counter() - t_start
            print(f"    [+] Huấn luyện xong trong: {train_duration:.2f} giây")

            # Đánh giá 5-Fold Cross Validation trên tập huấn luyện
            skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            X_cv = X_train_scaled[:30000] if use_scaled else X_train.iloc[:30000]
            y_cv = y_train.iloc[:30000]
            cv_scores = cross_val_score(clf, X_cv, y_cv, cv=skf, scoring="roc_auc", n_jobs=-1)
            cv_f1 = cross_val_score(clf, X_cv, y_cv, cv=skf, scoring="f1", n_jobs=-1)
            cv_roc_mean = round(float(np.mean(cv_scores)), 4)
            cv_roc_std = round(float(np.std(cv_scores)), 4)
            cv_f1_mean = round(float(np.mean(cv_f1)), 4)

            val_metrics = evaluate_model_performance(clf, X_val, X_val_scaled, y_val, is_linear=use_scaled)
            test_metrics = evaluate_model_performance(clf, X_test, X_test_scaled, y_test, is_linear=use_scaled)

            # Feature Importance (nếu có)
            feat_imp = {}
            if hasattr(clf, "feature_importances_"):
                imp = clf.feature_importances_
                feat_imp = {col: round(float(imp[i]), 4) for i, col in enumerate(FEATURE_COLS)}
            elif hasattr(clf, "coef_"):
                imp = np.abs(clf.coef_[0])
                feat_imp = {col: round(float(imp[i]), 4) for i, col in enumerate(FEATURE_COLS)}

            mlflow.log_metrics({
                "cv_roc_auc_mean": cv_roc_mean,
                "cv_roc_auc_std": cv_roc_std,
                "cv_f1_mean": cv_f1_mean,
                "val_accuracy": val_metrics["accuracy"],
                "val_f1_score": val_metrics["f1_score"],
                "val_roc_auc": val_metrics["roc_auc"],
                "test_accuracy": test_metrics["accuracy"],
                "test_f1_score": test_metrics["f1_score"],
                "test_roc_auc": test_metrics["roc_auc"],
                "train_duration_sec": round(train_duration, 2)
            })

            # Đăng ký mô hình vào MLflow Model Registry với Versioning thực tế
            reg_name = f"CustomerChurn_{name}"
            try:
                mlflow.sklearn.log_model(
                    sk_model=clf,
                    artifact_path="model",
                    registered_model_name=reg_name,
                    serialization_format="pickle"
                )
                print(f"    [+] Đã đăng ký mô hình vào MLflow Registry: {reg_name}")
            except Exception as e:
                print(f"    [-] Cảnh báo đăng ký MLflow: {e}")

            # Lưu mô hình cục bộ
            model_path = os.path.join(MODELS_DIR, f"{name.lower()}.joblib")
            joblib.dump(clf, model_path)
            mlflow.log_artifact(model_path)

            all_results[name] = {
                "params": cfg["params"],
                "train_duration_sec": round(train_duration, 2),
                "cv_5fold": {
                    "roc_auc_mean": cv_roc_mean,
                    "roc_auc_std": cv_roc_std,
                    "f1_mean": cv_f1_mean
                },
                "validation": val_metrics,
                "test": test_metrics,
                "feature_importance": feat_imp,
                "model_path": model_path
            }

            print(f"    - 5-Fold CV ROC-AUC: {cv_roc_mean:.4f} ± {cv_roc_std:.4f}")
            print(f"    - ROC-AUC (Test): {test_metrics['roc_auc']:.4f} | F1-Score: {test_metrics['f1_score']:.4f} | Time: {train_duration:.2f}s")

            if test_metrics["roc_auc"] > best_roc_auc:
                best_roc_auc = test_metrics["roc_auc"]
                best_model_name = name
                best_model_obj = clf
                best_is_scaled = use_scaled

    # Lưu Champion Model
    champion_path = os.path.join(MODELS_DIR, "champion_model.joblib")
    joblib.dump({
        "name": best_model_name,
        "model": best_model_obj,
        "use_scaled": best_is_scaled,
        "feature_names": FEATURE_COLS,
        "metrics": all_results[best_model_name]["test"]
    }, champion_path)

    # Đăng ký Champion Model vào MLflow Registry
    try:
        with mlflow.start_run(run_name="Champion_Model_Registration"):
            mlflow.sklearn.log_model(
                sk_model=best_model_obj,
                artifact_path="champion_model",
                registered_model_name="CustomerChurnChampion",
                serialization_format="pickle"
            )
            print("[+] Champion Model đã được đăng ký phiên bản mới vào Registry: CustomerChurnChampion")
    except Exception as e:
        print(f"[-] Cảnh báo đăng ký Champion: {e}")

    summary_file = os.path.join(MODELS_DIR, "evaluation_results.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "champion_model": best_model_name,
            "champion_roc_auc": best_roc_auc,
            "models": all_results
        }, f, indent=2, ensure_ascii=False)

    print("\n================== TỔNG HỢP SO SÁNH CÁC MÔ HÌNH ==================")
    print(f"{'Mô hình':<22} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'ROC-AUC':<10}")
    print("-" * 80)
    for m_name, m_data in all_results.items():
        t = m_data["test"]
        print(f"{m_name:<22} | {t['accuracy']:<10} | {t['precision']:<10} | {t['recall']:<10} | {t['f1_score']:<10} | {t['roc_auc']:<10}")
    print("=" * 80)
    print(f"[+] Champion Model được tuyển chọn: {best_model_name} (ROC-AUC: {best_roc_auc:.4f})")
    print(f"[+] Toàn bộ kết quả đã lưu vào: {summary_file}")
    return all_results


if __name__ == "__main__":
    train_and_track_all_models()
