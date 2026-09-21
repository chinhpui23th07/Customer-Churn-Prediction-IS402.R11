"""
FastAPI Model Serving Service cho ChurnGuard MLOps Platform.
Tích hợp Feast Feature Store Online, SHAP TreeExplainer, Inference Logging và Giám sát Drift.
Tuân thủ Invariant 01 (Clean Architecture) và Invariant 02 (< 400 dòng).
"""
import os
import sys
import time
import json
import sqlite3
import joblib
import numpy as np
import pandas as pd
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import shap

from src.api.schemas import (
    CustomerInput, PredictionResponse, BatchPredictionResponse, HealthResponse
)
from src.api.utils import (
    init_inference_db, log_inference_prediction, verify_api_key,
    prepare_feature_vector_from_input, compute_shap_attributions,
    generate_recommendation, FEATURE_COLS
)
from src.features.feature_store import query_online_features
from src.monitoring.drift_detector import run_drift_analysis

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")
ONLINE_STORE_DB = os.path.join(BASE_DIR, "data", "online_store.db")
MLFLOW_DB = os.path.join(BASE_DIR, "data", "mlflow.db")
WEB_DIR = os.path.join(BASE_DIR, "src", "web")

START_TIME = time.time()

app = FastAPI(
    title="ChurnGuard MLOps Serving API",
    description="REST API dự đoán khách hàng rời bỏ dịch vụ với Feast Feature Store và SHAP TreeExplainer.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Biến toàn cục lưu trữ Model, Scaler, Explainer và Metadata
MODEL_ARTIFACT = None
SCALER = None
METADATA = None
TREE_EXPLAINER = None


def load_artifacts():
    """Nạp Model, Scaler, SHAP Explainer và Metadata khi khởi động."""
    global MODEL_ARTIFACT, SCALER, METADATA, TREE_EXPLAINER
    champion_path = os.path.join(MODELS_DIR, "champion_model.joblib")
    scaler_path = os.path.join(PROCESSED_DIR, "scaler.joblib")
    meta_path = os.path.join(PROCESSED_DIR, "metadata.json")

    if os.path.exists(champion_path):
        MODEL_ARTIFACT = joblib.load(champion_path)
        clf = MODEL_ARTIFACT["model"]
        try:
            TREE_EXPLAINER = shap.TreeExplainer(clf)
        except Exception:
            TREE_EXPLAINER = None

    if os.path.exists(scaler_path):
        SCALER = joblib.load(scaler_path)
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            METADATA = json.load(f)
    init_inference_db()


@app.on_event("startup")
def startup_event():
    load_artifacts()


@app.get("/", tags=["General"])
def root():
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health_check():
    """Kiểm tra trạng thái sức khỏe toàn bộ các thành phần MLOps."""
    if MODEL_ARTIFACT is None:
        load_artifacts()

    model_name = MODEL_ARTIFACT["name"] if MODEL_ARTIFACT else "Not Loaded"
    feast_status = "CONNECTED (SQLite Online Registry)" if os.path.exists(ONLINE_STORE_DB) else "NOT_FOUND"
    mlflow_status = "CONNECTED (SQLite Backend)" if os.path.exists(MLFLOW_DB) else "NOT_FOUND"

    return HealthResponse(
        status="HEALTHY" if MODEL_ARTIFACT is not None else "DEGRADED",
        champion_model=model_name,
        model_version="v2.0.0-registered",
        feast_online_store=feast_status,
        mlflow_tracking_db=mlflow_status,
        uptime_seconds=round(time.time() - START_TIME, 2)
    )


@app.get("/metrics", tags=["Observability"])
def get_system_metrics():
    """Cung cấp metrics giám sát hệ thống (Prometheus/Observability standard)."""
    total_inferences = 0
    if os.path.exists(INFERENCE_DB):
        conn = sqlite3.connect(INFERENCE_DB)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM inference_logs")
        total_inferences = cur.fetchone()[0]
        conn.close()

    return {
        "service": "ChurnGuard-MLOps",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "total_inference_requests": total_inferences,
        "champion_model": MODEL_ARTIFACT["name"] if MODEL_ARTIFACT else "None",
        "feast_online_status": os.path.exists(ONLINE_STORE_DB)
    }


@app.get("/predict/customer/{customer_id}", response_model=PredictionResponse, tags=["Feature Store & Serving"])
def predict_from_feast_customer_id(customer_id: int, api_key: str = Depends(verify_api_key)):
    """
    Dự đoán trực tiếp bằng cách truy xuất Feast Online Store theo Customer ID.
    Nối liền luồng Feature Store -> Model Serving thời gian thực.
    """
    if MODEL_ARTIFACT is None:
        load_artifacts()

    t0 = time.perf_counter()
    online_data = query_online_features([customer_id])
    age_vals = online_data.get("customer_churn_features:age", online_data.get("age", [None]))
    if not online_data or not age_vals or age_vals[0] is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy khách hàng {customer_id} trong Feast Online Store!")

    feature_values = []
    for col in FEATURE_COLS:
        val_list = online_data.get(f"customer_churn_features:{col}", online_data.get(col, [0.0]))
        val = val_list[0] if val_list and val_list[0] is not None else 0.0
        feature_values.append(float(val))

    raw_vec = np.array([feature_values])
    clf = MODEL_ARTIFACT["model"]
    use_scaled = MODEL_ARTIFACT["use_scaled"]
    x_input = SCALER.transform(raw_vec) if use_scaled and SCALER is not None else raw_vec

    pred_class = int(clf.predict(x_input)[0])
    prob = float(clf.predict_proba(x_input)[0][1]) if hasattr(clf, "predict_proba") else float(pred_class)
    latency = (time.perf_counter() - t0) * 1000.0

    risk_tier = "High Risk" if prob >= 0.70 else ("Medium Risk" if prob >= 0.35 else "Low Risk")
    rec = generate_recommendation(prob, feature_values[4], feature_values[5])
    xai_factors, xai_summary = compute_shap_attributions(TREE_EXPLAINER, x_input)
    log_inference_prediction(customer_id, feature_values, pred_class, prob)

    return PredictionResponse(
        customer_id=customer_id,
        churn_prediction=pred_class,
        churn_probability=round(prob, 4),
        risk_level=risk_tier,
        recommended_action=rec,
        feature_attributions=xai_factors,
        explanation_summary=xai_summary,
        latency_ms=round(latency, 2)
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_single(customer: CustomerInput, api_key: str = Depends(verify_api_key)):
    """Dự đoán thời gian thực cho một khách hàng gửi qua JSON kèm giải thích SHAP."""
    if MODEL_ARTIFACT is None:
        load_artifacts()

    t0 = time.perf_counter()
    raw_vec = prepare_feature_vector_from_input(customer)
    clf = MODEL_ARTIFACT["model"]
    use_scaled = MODEL_ARTIFACT["use_scaled"]
    x_input = SCALER.transform(raw_vec) if use_scaled and SCALER is not None else raw_vec

    pred_class = int(clf.predict(x_input)[0])
    prob = float(clf.predict_proba(x_input)[0][1]) if hasattr(clf, "predict_proba") else float(pred_class)
    latency = (time.perf_counter() - t0) * 1000.0

    risk_tier = "High Risk" if prob >= 0.70 else ("Medium Risk" if prob >= 0.35 else "Low Risk")
    rec = generate_recommendation(prob, customer.support_calls, customer.payment_delay)
    xai_factors, xai_summary = compute_shap_attributions(TREE_EXPLAINER, x_input)
    log_inference_prediction(customer.customer_id or 999999, raw_vec[0].tolist(), pred_class, prob)

    return PredictionResponse(
        customer_id=customer.customer_id,
        churn_prediction=pred_class,
        churn_probability=round(prob, 4),
        risk_level=risk_tier,
        recommended_action=rec,
        feature_attributions=xai_factors,
        explanation_summary=xai_summary,
        latency_ms=round(latency, 2)
    )


@app.post("/batch_predict", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_batch(customers: List[CustomerInput], api_key: str = Depends(verify_api_key)):
    """Dự đoán hàng loạt cho danh sách khách hàng gửi qua JSON."""
    results = [predict_single(c) for c in customers]
    churn_cnt = sum(1 for r in results if r.churn_prediction == 1)
    risk_dist = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}
    for r in results:
        risk_dist[r.risk_level] += 1

    total = len(customers)
    return BatchPredictionResponse(
        total_processed=total,
        churn_count=churn_cnt,
        retention_count=total - churn_cnt,
        overall_churn_rate=round(churn_cnt / max(total, 1), 4),
        risk_distribution=risk_dist,
        predictions=results
    )


@app.post("/upload_csv_predict", tags=["Inference"])
async def predict_from_csv(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """Dự đoán hàng loạt trực tiếp từ tệp CSV tải lên."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Vui lòng chỉ tải lên tệp định dạng CSV!")

    df = pd.read_csv(file.file)
    required = ["Age", "Gender", "Tenure", "Usage Frequency", "Support Calls",
                "Payment Delay", "Subscription Type", "Contract Length", "Total Spend", "Last Interaction"]
    for col in required:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Tệp CSV thiếu cột bắt buộc: {col}")

    inputs = []
    for _, row in df.iterrows():
        inputs.append(CustomerInput(
            customer_id=int(row.get("CustomerID", 0)),
            age=float(row["Age"]),
            gender=str(row["Gender"]),
            tenure=float(row["Tenure"]),
            usage_frequency=float(row["Usage Frequency"]),
            support_calls=float(row["Support Calls"]),
            payment_delay=float(row["Payment Delay"]),
            subscription_type=str(row["Subscription Type"]),
            contract_length=str(row["Contract Length"]),
            total_spend=float(row["Total Spend"]),
            last_interaction=float(row["Last Interaction"])
        ))

    return predict_batch(inputs)


@app.get("/features/{customer_id}", tags=["Feature Store"])
def get_features_by_id(customer_id: int):
    """Truy xuất đặc trưng online từ Feast Online Store."""
    try:
        data = query_online_features([customer_id])
        return {"customer_id": customer_id, "features": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy xuất Feast: {str(e)}")


@app.get("/drift/status", tags=["Monitoring"])
def get_drift_status():
    """Truy vấn báo cáo giám sát Data Drift thời gian thực."""
    metrics_path = os.path.join(PROCESSED_DIR, "drift_metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return run_drift_analysis()


@app.post("/api/v1/trigger_retrain", tags=["MLOps Automation"])
def trigger_retraining(force: bool = False, api_key: str = Depends(verify_api_key)):
    """Kích hoạt webhook tái huấn luyện mô hình khi phát hiện Concept/Data Drift."""
    drift_res = run_drift_analysis()
    if drift_res.get("dataset_drift_detected", False) or force:
        return {
            "status": "TRIGGERED",
            "message": "Đã kích hoạt tái huấn luyện thành công qua MLOps Pipeline.",
            "drift_share": drift_res.get("drift_share", 0.0),
            "triggered_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }
    return {
        "status": "SKIPPED",
        "message": "Dữ liệu vẫn ổn định (PSI < 0.25). Không cần tái huấn luyện.",
        "drift_share": drift_res.get("drift_share", 0.0)
    }


@app.get("/models/summary", tags=["Analytics"])
def get_models_summary():
    """Truy xuất tổng hợp so sánh các mô hình và Champion Model."""
    summary_path = os.path.join(MODELS_DIR, "evaluation_results.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Chưa tìm thấy tệp kết quả mô hình!")


if os.path.exists(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")
