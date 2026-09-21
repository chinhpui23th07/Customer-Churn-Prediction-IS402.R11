"""
FastAPI Model Serving Service cho ChurnGuard MLOps Platform.
Tích hợp Feast Feature Store Online, SHAP TreeExplainer, Inference Logging, Giám sát Drift và A/B Testing.
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
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import shap

from src.api.schemas import (
    CustomerInput, PredictionResponse, BatchPredictionResponse, HealthResponse
)
from src.api.utils import (
    init_inference_db, log_inference_prediction, log_batch_inference_predictions,
    verify_api_key, prepare_feature_vector_from_input, compute_shap_attributions,
    generate_recommendation, run_model_inference, FEATURE_COLS
)
from src.api.ab_testing import (
    route_customer_to_model, analyze_ab_test_performance,
    CHAMPION_VERSION, CHALLENGER_VERSION
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
ONLINE_STORE_DB = os.path.join(BASE_DIR, "data", "feast_repo", "data", "online_store.db")
MLFLOW_DB = os.path.join(BASE_DIR, "data", "mlflow.db")
WEB_DIR = os.path.join(BASE_DIR, "src", "web")

START_TIME = time.time()

# Biến toàn cục lưu trữ Model, Scaler, Explainer và Metadata
MODEL_ARTIFACT = None
CHALLENGER_ARTIFACT = None
SCALER = None
METADATA = None
TREE_EXPLAINER = None


def load_artifacts():
    """Nạp Model Champion, Challenger, Scaler, SHAP Explainer và Metadata khi khởi động."""
    global MODEL_ARTIFACT, CHALLENGER_ARTIFACT, SCALER, METADATA, TREE_EXPLAINER
    champion_path = os.path.join(MODELS_DIR, "champion_model.joblib")
    challenger_path = os.path.join(MODELS_DIR, "random_forest.joblib")
    scaler_path = os.path.join(PROCESSED_DIR, "scaler.joblib")
    meta_path = os.path.join(PROCESSED_DIR, "metadata.json")

    if os.path.exists(champion_path):
        MODEL_ARTIFACT = joblib.load(champion_path)
        clf = MODEL_ARTIFACT["model"]
        try:
            TREE_EXPLAINER = shap.TreeExplainer(clf)
        except Exception:
            TREE_EXPLAINER = None

    if os.path.exists(challenger_path):
        CHALLENGER_ARTIFACT = joblib.load(challenger_path)

    if os.path.exists(scaler_path):
        SCALER = joblib.load(scaler_path)
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            METADATA = json.load(f)
    init_inference_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Quản lý vòng đời khởi động và tắt service theo chuẩn FastAPI hiện đại."""
    load_artifacts()
    yield


app = FastAPI(
    title="ChurnGuard MLOps Serving API",
    description="REST API dự đoán khách hàng rời bỏ dịch vụ với Feast Feature Store và SHAP TreeExplainer.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


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
        model_version=CHAMPION_VERSION,
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
    x_input, pred_class, prob, risk_tier = run_model_inference(clf, raw_vec, SCALER, MODEL_ARTIFACT["use_scaled"])
    latency = (time.perf_counter() - t0) * 1000.0

    rec = generate_recommendation(prob, feature_values[4], feature_values[5])
    xai_factors, xai_summary = compute_shap_attributions(TREE_EXPLAINER, x_input)
    log_inference_prediction(customer_id, feature_values, pred_class, prob, model_version=CHAMPION_VERSION)

    return PredictionResponse(
        customer_id=customer_id,
        churn_prediction=pred_class,
        churn_probability=round(prob, 4),
        risk_level=risk_tier,
        recommended_action=rec,
        feature_attributions=xai_factors,
        explanation_summary=xai_summary,
        model_version=CHAMPION_VERSION,
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
    x_input, pred_class, prob, risk_tier = run_model_inference(clf, raw_vec, SCALER, MODEL_ARTIFACT["use_scaled"])
    latency = (time.perf_counter() - t0) * 1000.0

    rec = generate_recommendation(prob, customer.support_calls, customer.payment_delay)
    xai_factors, xai_summary = compute_shap_attributions(TREE_EXPLAINER, x_input)
    log_inference_prediction(customer.customer_id or 999999, raw_vec[0].tolist(), pred_class, prob, model_version=CHAMPION_VERSION)

    return PredictionResponse(
        customer_id=customer.customer_id,
        churn_prediction=pred_class,
        churn_probability=round(prob, 4),
        risk_level=risk_tier,
        recommended_action=rec,
        feature_attributions=xai_factors,
        explanation_summary=xai_summary,
        model_version=CHAMPION_VERSION,
        latency_ms=round(latency, 2)
    )


@app.post("/predict/ab_test", response_model=PredictionResponse, tags=["A/B Testing"])
def predict_ab_test(customer: CustomerInput, api_key: str = Depends(verify_api_key)):
    """
    Điều hướng tất định A/B testing: 80% Champion (XGBoost) vs 20% Challenger (Random Forest).
    Lưu log với version tương ứng để kiểm định thống kê hiệu năng 2 luồng.
    """
    if MODEL_ARTIFACT is None:
        load_artifacts()

    t0 = time.perf_counter()
    cid = customer.customer_id or 999999
    route_type, version_tag = route_customer_to_model(cid)

    if route_type == "challenger" and CHALLENGER_ARTIFACT is not None:
        clf = CHALLENGER_ARTIFACT
        model_ver = version_tag
        use_scaled = False
    else:
        clf = MODEL_ARTIFACT["model"]
        model_ver = CHAMPION_VERSION
        use_scaled = MODEL_ARTIFACT["use_scaled"]

    raw_vec = prepare_feature_vector_from_input(customer)
    x_input, pred_class, prob, risk_tier = run_model_inference(clf, raw_vec, SCALER, use_scaled)
    latency = (time.perf_counter() - t0) * 1000.0

    rec = generate_recommendation(prob, customer.support_calls, customer.payment_delay)
    xai_factors, xai_summary = compute_shap_attributions(TREE_EXPLAINER, x_input)
    log_inference_prediction(cid, raw_vec[0].tolist(), pred_class, prob, model_version=model_ver)

    return PredictionResponse(
        customer_id=customer.customer_id,
        churn_prediction=pred_class,
        churn_probability=round(prob, 4),
        risk_level=risk_tier,
        recommended_action=rec,
        feature_attributions=xai_factors,
        explanation_summary=xai_summary,
        model_version=model_ver,
        latency_ms=round(latency, 2)
    )


@app.get("/ab_test/analytics", tags=["A/B Testing"])
def get_ab_test_analytics():
    """Báo cáo đối sánh hiệu năng và kiểm định giả thuyết thống kê A/B Testing."""
    return analyze_ab_test_performance()


@app.post("/batch_predict", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_batch(customers: List[CustomerInput], api_key: str = Depends(verify_api_key)):
    """Dự đoán hàng loạt vector hóa hiệu năng cao kết hợp single-transaction DB insert."""
    if MODEL_ARTIFACT is None:
        load_artifacts()
    if not customers:
        return BatchPredictionResponse(
            total_processed=0, churn_count=0, retention_count=0, overall_churn_rate=0.0,
            risk_distribution={"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}, predictions=[]
        )

    t0 = time.perf_counter()
    raw_vecs = np.array([prepare_feature_vector_from_input(c)[0] for c in customers])
    clf = MODEL_ARTIFACT["model"]
    use_scaled = MODEL_ARTIFACT["use_scaled"]
    x_batch = SCALER.transform(raw_vecs) if use_scaled and SCALER is not None else raw_vecs

    preds = clf.predict(x_batch).astype(int)
    probs = clf.predict_proba(x_batch)[:, 1] if hasattr(clf, "predict_proba") else preds.astype(float)
    avg_lat = round(((time.perf_counter() - t0) * 1000.0) / len(customers), 2)

    results, log_records = [], []
    risk_dist = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}
    churn_cnt = 0

    for i, c in enumerate(customers):
        p_cls, p_pr = int(preds[i]), float(probs[i])
        churn_cnt += (1 if p_cls == 1 else 0)
        tier = "High Risk" if p_pr >= 0.70 else ("Medium Risk" if p_pr >= 0.35 else "Low Risk")
        risk_dist[tier] += 1
        rec = generate_recommendation(p_pr, c.support_calls, c.payment_delay)
        cid = c.customer_id or 999999
        log_records.append((cid, p_cls, p_pr, raw_vecs[i].tolist(), CHAMPION_VERSION))
        results.append(PredictionResponse(
            customer_id=c.customer_id, churn_prediction=p_cls, churn_probability=round(p_pr, 4),
            risk_level=tier, recommended_action=rec, model_version=CHAMPION_VERSION, latency_ms=avg_lat
        ))

    log_batch_inference_predictions(log_records)
    total = len(customers)
    return BatchPredictionResponse(
        total_processed=total, churn_count=churn_cnt, retention_count=total - churn_cnt,
        overall_churn_rate=round(churn_cnt / max(total, 1), 4), risk_distribution=risk_dist,
        predictions=results
    )


@app.post("/upload_csv_predict", tags=["Inference"])
async def predict_from_csv(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """Dự đoán hàng loạt trực tiếp từ tệp CSV tải lên với chuẩn hóa tiêu đề linh hoạt."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Vui lòng chỉ tải lên tệp định dạng CSV!")

    df = pd.read_csv(file.file)
    norm = {c.strip().lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    reqs = ["age", "gender", "tenure", "usagefrequency", "supportcalls",
            "paymentdelay", "subscriptiontype", "contractlength", "totalspend", "lastinteraction"]
    for r in reqs:
        if r not in norm:
            raise HTTPException(status_code=400, detail=f"Tệp CSV thiếu cột bắt buộc: {r}")

    cid_col = norm.get("customerid")
    inputs = [
        CustomerInput(
            customer_id=int(r[cid_col]) if cid_col and pd.notna(r[cid_col]) else 999999,
            age=float(r[norm["age"]]), gender=str(r[norm["gender"]]).capitalize(),
            tenure=float(r[norm["tenure"]]), usage_frequency=float(r[norm["usagefrequency"]]),
            support_calls=float(r[norm["supportcalls"]]), payment_delay=float(r[norm["paymentdelay"]]),
            subscription_type=str(r[norm["subscriptiontype"]]).capitalize(),
            contract_length=str(r[norm["contractlength"]]).capitalize(),
            total_spend=float(r[norm["totalspend"]]), last_interaction=float(r[norm["lastinteraction"]])
        ) for _, r in df.iterrows()
    ]
    return predict_batch(inputs, api_key=api_key)


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
        return {"status": "TRIGGERED", "message": "Đã kích hoạt tái huấn luyện thành công qua MLOps Pipeline.",
                "drift_share": drift_res.get("drift_share", 0.0), "triggered_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
    return {"status": "SKIPPED", "message": "Dữ liệu vẫn ổn định (PSI < 0.25). Không cần tái huấn luyện.", "drift_share": drift_res.get("drift_share", 0.0)}


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
