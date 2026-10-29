"""FastAPI Model Serving Service cho ChurnGuard MLOps Platform."""
import os
import sys
import time
import json
import math
import threading
import joblib
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from pydantic import ValidationError
import shap

from src.api.schemas import (
    CustomerInput, PredictionResponse, BatchPredictionResponse, HealthResponse, MAX_BATCH_SIZE
)
from src.api.utils import (
    init_inference_db, log_inference_prediction, log_batch_inference_predictions,
    verify_api_key, prepare_feature_vector_from_input, compute_shap_attributions,
    generate_recommendation, run_model_inference, check_feast_online_status, FEATURE_COLS
)
from src.api.ab_testing import route_customer_to_model, CHAMPION_VERSION, CHALLENGER_VERSION
from src.features.feature_store import query_online_features
from src.api.routes_management import router as management_router, register_reload_hook

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"): sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")
ONLINE_STORE_DB = os.path.join(BASE_DIR, "data", "feast_repo", "data", "online_store.db")
MLFLOW_DB = os.path.join(BASE_DIR, "data", "mlflow.db")
WEB_DIR = os.path.join(BASE_DIR, "src", "web")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

START_TIME = time.time()
MODEL_LOCK = threading.RLock()  # thread-safe reload lock (supersedes threading.Lock)

MODEL_ARTIFACT = None
CHALLENGER_ARTIFACT = None
SCALER = None
METADATA = None
TREE_EXPLAINER = None
CHALLENGER_TREE_EXPLAINER = None


def _build_shap_explainer(clf):
    """Khởi tạo SHAP TreeExplainer với fallback tự động sang LinearExplainer."""
    try:
        return shap.TreeExplainer(clf)
    except Exception:
        try:
            return shap.LinearExplainer(clf, np.zeros((1, len(FEATURE_COLS))))
        except Exception:
            return None


def load_artifacts():
    """Nạp Model Champion, Challenger, Scaler và SHAP Explainer an toàn đa luồng."""
    global MODEL_ARTIFACT, CHALLENGER_ARTIFACT, SCALER, METADATA, TREE_EXPLAINER, CHALLENGER_TREE_EXPLAINER
    with MODEL_LOCK:
        champion_path = os.path.join(MODELS_DIR, "champion_model.joblib")
        challenger_path = os.path.join(MODELS_DIR, "random_forest.joblib")
        scaler_path = os.path.join(PROCESSED_DIR, "scaler.joblib")
        meta_path = os.path.join(PROCESSED_DIR, "metadata.json")

        if os.path.exists(champion_path):
            MODEL_ARTIFACT = joblib.load(champion_path)

        if os.getenv("USE_MLFLOW_REGISTRY", "false").lower() == "true":
            try:
                os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
                import mlflow.sklearn
                mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{MLFLOW_DB.replace(chr(92), '/')}")
                mlflow.set_tracking_uri(mlflow_uri)
                registry_model = mlflow.sklearn.load_model("models:/CustomerChurnChampion/Production")
                if registry_model is not None:
                    MODEL_ARTIFACT = {"name": "CustomerChurnChampion (MLflow Registry)", "model": registry_model, "use_scaled": False}
            except Exception:
                pass

        if MODEL_ARTIFACT is not None:
            clf = MODEL_ARTIFACT["model"]
            try:
                TREE_EXPLAINER = shap.TreeExplainer(clf)
            except Exception:
                try:
                    TREE_EXPLAINER = shap.LinearExplainer(clf, np.zeros((1, len(FEATURE_COLS))))
                except Exception:
                    TREE_EXPLAINER = None

        if os.path.exists(challenger_path):
            CHALLENGER_ARTIFACT = joblib.load(challenger_path)
            CHALLENGER_TREE_EXPLAINER = _build_shap_explainer(CHALLENGER_ARTIFACT)
        if os.path.exists(scaler_path):
            SCALER = joblib.load(scaler_path)
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                METADATA = json.load(f)
        init_inference_db()
        return {"status": "SUCCESS", "champion_model": MODEL_ARTIFACT.get("name") if MODEL_ARTIFACT else "None"}


register_reload_hook(load_artifacts)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_artifacts()
    yield


app = FastAPI(
    title="ChurnGuard MLOps Serving API",
    description="REST API dự đoán khách hàng rời bỏ dịch vụ với Feast Feature Store và SHAP TreeExplainer.",
    version="2.0.0",
    lifespan=lifespan
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(management_router)


@app.get("/", tags=["General"])
def root():
    return RedirectResponse(url="/docs")


@app.get("/docs/drift_report.html", tags=["Monitoring"])
def serve_drift_report_html():
    """Phục vụ báo cáo giám sát Data Drift định dạng HTML cho giao diện Web UI."""
    html_path = os.path.join(DOCS_DIR, "drift_report.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")

    drift_data: Dict[str, Any] = {}
    for fname in ("drift_report.json", "drift_metrics.json"):
        p = os.path.join(PROCESSED_DIR, fname)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    drift_data = json.load(f)
                break
            except Exception:
                pass

    rows_html = "".join(
        f"<tr><td>{k}</td><td>{float(v.get('psi_score', 0.0)):.4f}</td>"
        f"<td>{float(v.get('ks_p_value', 1.0)):.4f}</td><td>{'DRIFT' if v.get('drift_detected') else 'STABLE'}</td></tr>"
        for k, v in drift_data.get("features", {}).items() if isinstance(v, dict)
    )
    html_content = (
        "<!DOCTYPE html><html lang='vi'><head><meta charset='utf-8'><title>ChurnGuard Data Drift Report</title>"
        "<style>body{font-family:sans-serif;margin:2rem;background:#0f172a;color:#f8fafc}"
        "table{width:100%;border-collapse:collapse;margin-top:1rem}th,td{border:1px solid #334155;padding:0.6rem}</style>"
        f"</head><body><h1>Báo cáo Giám sát Data Drift (KS-Test & PSI)</h1><table><thead>"
        f"<tr><th>Đặc trưng</th><th>PSI</th><th>KS p-value</th><th>Trạng thái</th></tr></thead><tbody>{rows_html}</tbody></table></body></html>"
    )
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health_check():
    """Kiểm tra trạng thái sức khỏe toàn bộ các thành phần MLOps."""
    if MODEL_ARTIFACT is None:
        load_artifacts()
    return HealthResponse(
        status="HEALTHY" if MODEL_ARTIFACT is not None else "DEGRADED",
        champion_model=MODEL_ARTIFACT["name"] if MODEL_ARTIFACT else "Not Loaded",
        model_version=CHAMPION_VERSION,
        feast_online_store=check_feast_online_status(ONLINE_STORE_DB),
        mlflow_tracking_db="CONNECTED (MLflow Tracking & Registry)" if os.path.exists(MLFLOW_DB) else "NOT_FOUND",
        uptime_seconds=round(time.time() - START_TIME, 2)
    )


def _execute_feast_online_prediction(customer_id: int) -> PredictionResponse:
    """Truy xuất đặc trưng từ Feast Online Store và thực thi dự đoán trực tuyến."""
    if MODEL_ARTIFACT is None:
        load_artifacts()

    t0 = time.perf_counter()
    online_data = query_online_features([customer_id])
    if not online_data:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy khách hàng {customer_id} trong Feast Online Store!")

    feature_values, missing_cols = [], []
    for col in FEATURE_COLS:
        val_list = online_data.get(f"customer_churn_features:{col}", online_data.get(col, [None]))
        val = val_list[0] if isinstance(val_list, list) and len(val_list) > 0 else None
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            missing_cols.append(col)
        else:
            feature_values.append(float(val))

    if missing_cols:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy khách hàng {customer_id} hoặc thiếu đặc trưng: {missing_cols}")

    raw_vec = np.array([feature_values])
    with MODEL_LOCK:
        clf, use_scaled, explainer = MODEL_ARTIFACT["model"], MODEL_ARTIFACT["use_scaled"], TREE_EXPLAINER

    x_input, pred_class, prob, risk_tier = run_model_inference(clf, raw_vec, SCALER, use_scaled)
    latency = (time.perf_counter() - t0) * 1000.0
    con_code = int(round(feature_values[7]))
    con_str = "Annual" if con_code == 2 else ("Quarterly" if con_code == 1 else "Monthly")
    rec = generate_recommendation(prob, feature_values[4], feature_values[5], feature_values[8], con_str, feature_values[2])
    xai_factors, xai_summary = compute_shap_attributions(explainer, x_input, model=clf)
    log_inference_prediction(customer_id, feature_values, pred_class, prob, model_version=CHAMPION_VERSION)

    return PredictionResponse(
        customer_id=customer_id, churn_prediction=pred_class, churn_probability=round(prob, 4),
        risk_level=risk_tier, recommended_action=rec, feature_attributions=xai_factors,
        explanation_summary=xai_summary, model_version=CHAMPION_VERSION, latency_ms=round(latency, 2)
    )


@app.get("/predict/customer/{customer_id}", response_model=PredictionResponse, tags=["Feature Store & Serving"])
def predict_from_feast_customer_id(customer_id: int, api_key: str = Depends(verify_api_key)):
    return _execute_feast_online_prediction(customer_id)


@app.get("/predict/feast/online/{customer_id}", response_model=PredictionResponse, tags=["Feature Store & Serving"])
def predict_feast_online_get(customer_id: int, api_key: str = Depends(verify_api_key)):
    return _execute_feast_online_prediction(customer_id)


@app.post("/predict/feast/online", response_model=PredictionResponse, tags=["Feature Store & Serving"])
def predict_feast_online_post(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    customer_id: Optional[int] = None,
    api_key: str = Depends(verify_api_key),
):
    cid = customer_id if customer_id is not None else (payload.get("customer_id") if isinstance(payload, dict) else None)
    if cid is None:
        raise HTTPException(status_code=422, detail="Vui lòng cung cấp customer_id hợp lệ!")
    return _execute_feast_online_prediction(int(cid))


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_single(customer: CustomerInput, api_key: str = Depends(verify_api_key)):
    if MODEL_ARTIFACT is None:
        load_artifacts()
    t0 = time.perf_counter()
    raw_vec = prepare_feature_vector_from_input(customer)
    with MODEL_LOCK:
        clf, use_scaled, explainer = MODEL_ARTIFACT["model"], MODEL_ARTIFACT["use_scaled"], TREE_EXPLAINER

    x_input, pred_class, prob, risk_tier = run_model_inference(clf, raw_vec, SCALER, use_scaled, customer=customer)
    latency = (time.perf_counter() - t0) * 1000.0
    rec = generate_recommendation(prob, customer.support_calls, customer.payment_delay, customer.total_spend, customer.contract_length, customer.tenure)
    xai_factors, xai_summary = compute_shap_attributions(explainer, x_input, model=clf)
    cid = customer.customer_id if customer.customer_id is not None else 999999
    log_inference_prediction(cid, raw_vec[0].tolist(), pred_class, prob, model_version=CHAMPION_VERSION)

    return PredictionResponse(
        customer_id=customer.customer_id, churn_prediction=pred_class, churn_probability=round(prob, 4),
        risk_level=risk_tier, recommended_action=rec, feature_attributions=xai_factors,
        explanation_summary=xai_summary, model_version=CHAMPION_VERSION, latency_ms=round(latency, 2)
    )


@app.post("/predict/ab_test", response_model=PredictionResponse, tags=["A/B Testing"])
def predict_ab_test(customer: CustomerInput, api_key: str = Depends(verify_api_key)):
    if MODEL_ARTIFACT is None:
        load_artifacts()
    t0 = time.perf_counter()
    cid = customer.customer_id if customer.customer_id is not None else 999999
    route_type, version_tag = route_customer_to_model(cid)

    with MODEL_LOCK:
        if route_type == "challenger" and CHALLENGER_ARTIFACT is not None:
            clf, model_ver, use_scaled = CHALLENGER_ARTIFACT, version_tag, False
            active_explainer = CHALLENGER_TREE_EXPLAINER if CHALLENGER_TREE_EXPLAINER is not None else TREE_EXPLAINER
        else:
            clf, model_ver, use_scaled = MODEL_ARTIFACT["model"], CHAMPION_VERSION, MODEL_ARTIFACT["use_scaled"]
            active_explainer = TREE_EXPLAINER

    raw_vec = prepare_feature_vector_from_input(customer)
    x_input, pred_class, prob, risk_tier = run_model_inference(clf, raw_vec, SCALER, use_scaled, customer=customer)
    latency = (time.perf_counter() - t0) * 1000.0
    rec = generate_recommendation(prob, customer.support_calls, customer.payment_delay, customer.total_spend, customer.contract_length, customer.tenure)
    xai_factors, xai_summary = compute_shap_attributions(active_explainer, x_input, model=clf)
    log_inference_prediction(cid, raw_vec[0].tolist(), pred_class, prob, model_version=model_ver)

    return PredictionResponse(
        customer_id=customer.customer_id, churn_prediction=pred_class, churn_probability=round(prob, 4),
        risk_level=risk_tier, recommended_action=rec, feature_attributions=xai_factors,
        explanation_summary=xai_summary, model_version=model_ver, latency_ms=round(latency, 2)
    )


@app.post("/batch_predict", response_model=BatchPredictionResponse, tags=["Inference"])
def predict_batch(customers: List[CustomerInput], api_key: str = Depends(verify_api_key)):
    if MODEL_ARTIFACT is None:
        load_artifacts()
    if len(customers) > MAX_BATCH_SIZE:
        raise HTTPException(status_code=422, detail=f"Batch size exceeds maximum limit of {MAX_BATCH_SIZE}")
    if not customers:
        return BatchPredictionResponse(
            total_processed=0, churn_count=0, retention_count=0, overall_churn_rate=0.0,
            risk_distribution={"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}, predictions=[]
        )

    t0 = time.perf_counter()
    raw_vecs = np.array([prepare_feature_vector_from_input(c)[0] for c in customers])
    with MODEL_LOCK:
        clf, use_scaled = MODEL_ARTIFACT["model"], MODEL_ARTIFACT["use_scaled"]

    x_batch = SCALER.transform(raw_vecs) if use_scaled and SCALER is not None else raw_vecs
    x_batch_df = pd.DataFrame(x_batch, columns=FEATURE_COLS)
    x_eval = x_batch_df if hasattr(clf, "feature_names_in_") else x_batch

    preds = clf.predict(x_eval).astype(int)
    probs = clf.predict_proba(x_eval)[:, 1] if hasattr(clf, "predict_proba") else preds.astype(float)
    avg_lat = round(((time.perf_counter() - t0) * 1000.0) / len(customers), 2)

    results, log_records = [], []
    risk_dist = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}
    churn_cnt = 0

    for i, c in enumerate(customers):
        p_cls, p_pr = int(preds[i]), float(probs[i])
        churn_cnt += (1 if p_cls == 1 else 0)
        tier = "High Risk" if p_pr >= 0.70 else ("Medium Risk" if p_pr >= 0.40 else "Low Risk")
        risk_dist[tier] += 1
        rec = generate_recommendation(p_pr, c.support_calls, c.payment_delay, c.total_spend, c.contract_length, c.tenure)
        cid = c.customer_id if c.customer_id is not None else 999999
        log_records.append((cid, p_cls, p_pr, raw_vecs[i].tolist(), CHAMPION_VERSION))
        results.append(PredictionResponse(
            customer_id=c.customer_id, churn_prediction=p_cls, churn_probability=round(p_pr, 4),
            risk_level=tier, recommended_action=rec, model_version=CHAMPION_VERSION, latency_ms=avg_lat
        ))

    log_batch_inference_predictions(log_records)
    total = len(customers)
    return BatchPredictionResponse(
        total_processed=total, churn_count=churn_cnt, retention_count=total - churn_cnt,
        overall_churn_rate=round(churn_cnt / max(total, 1), 4), risk_distribution=risk_dist, predictions=results
    )


@app.post("/upload_csv_predict", tags=["Inference"])
async def predict_from_csv(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Vui lòng chỉ tải lên tệp định dạng CSV!")
    try:
        df = pd.read_csv(file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không thể đọc tệp CSV: {str(e)}")
    if len(df) > MAX_BATCH_SIZE:
        raise HTTPException(status_code=422, detail=f"Batch size exceeds maximum limit of {MAX_BATCH_SIZE}")

    norm = {c.strip().lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    reqs = ["age", "gender", "tenure", "usagefrequency", "supportcalls",
            "paymentdelay", "subscriptiontype", "contractlength", "totalspend", "lastinteraction"]
    for r in reqs:
        if r not in norm:
            raise HTTPException(status_code=400, detail=f"Tệp CSV thiếu cột bắt buộc: {r}")

    cid_col = norm.get("customerid")
    inputs: List[CustomerInput] = []
    try:
        for row_idx, r in df.iterrows():
            for req_key in reqs:
                if pd.isna(r[norm[req_key]]):
                    raise ValueError(f"Dòng {row_idx + 1}: Cột '{norm[req_key]}' chứa giá trị trống (NaN)")
            raw_cid = r[cid_col] if cid_col and pd.notna(r[cid_col]) else 999999
            cid_int = int(float(raw_cid)) if not isinstance(raw_cid, str) or raw_cid.strip().isdigit() else int(raw_cid)
            inputs.append(CustomerInput(
                customer_id=cid_int, age=float(r[norm["age"]]),
                gender=str(r[norm["gender"]]).strip().capitalize(),
                tenure=float(r[norm["tenure"]]), usage_frequency=float(r[norm["usagefrequency"]]),
                support_calls=float(r[norm["supportcalls"]]), payment_delay=float(r[norm["paymentdelay"]]),
                subscription_type=str(r[norm["subscriptiontype"]]).strip().capitalize(),
                contract_length=str(r[norm["contractlength"]]).strip().capitalize(),
                total_spend=float(r[norm["totalspend"]]), last_interaction=float(r[norm["lastinteraction"]])
            ))
    except (ValueError, KeyError, TypeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"Dữ liệu CSV không hợp lệ: {str(exc)}")

    return predict_batch(inputs, api_key=api_key)

if os.path.exists(WEB_DIR):
    app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")
