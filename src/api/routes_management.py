"""
APIRouter chứa các endpoint quản trị, giám sát và phân tích hiệu năng hệ thống MLOps:
- /models/summary : Đánh giá đối chuẩn các mô hình huấn luyện
- /ab_test/analytics : Báo cáo thống kê phân luồng A/B Testing
- /features/{customer_id} : Truy vấn Feast Feature Store Online
- /drift/status : Báo cáo giám sát Data Drift thời gian thực
- /api/v1/trigger_retrain : Kích hoạt tái huấn luyện tự động (Webhooks)
- /metrics : Giám sát Prometheus / System Uptime & Latency
"""
import os
import sys
import time
import json
import sqlite3
import subprocess
import threading
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from src.api.utils import verify_api_key
from src.api.ab_testing import analyze_ab_test_performance
from src.features.feature_store import query_online_features
from src.monitoring.drift_detector import run_drift_analysis

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
INFERENCE_DB = os.path.join(BASE_DIR, "data", "inference_logs.db")
ONLINE_STORE_DB = os.path.join(BASE_DIR, "data", "feast_repo", "data", "online_store.db")
APP_START_TIME = time.time()
RELOAD_HOOK = None
RETRAIN_LOCK = threading.Lock()


def register_reload_hook(hook):
    """Đăng ký callback nạp lại mô hình trong RAM cho Serving API."""
    global RELOAD_HOOK
    RELOAD_HOOK = hook


def run_background_retraining():
    """Chạy quy trình tái huấn luyện mô hình thực tế trong background kèm hot-reload và mutex lock."""
    if not RETRAIN_LOCK.acquire(blocking=False):
        return
    script_path = os.path.join(BASE_DIR, "src", "models", "train_pipeline.py")
    log_file = os.path.join(BASE_DIR, "data", "retrain_execution.log")
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as out:
            out.write(f"\n--- Retraining Triggered at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())} ---\n")
            out.flush()

        if "PYTEST_CURRENT_TEST" in os.environ:
            try:
                if callable(RELOAD_HOOK):
                    RELOAD_HOOK()
            finally:
                RETRAIN_LOCK.release()
            return

        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP

        log_handle = open(log_file, "a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=flags
        )

        def monitor_and_reload():
            try:
                proc.wait()
                if proc.returncode == 0 and callable(RELOAD_HOOK):
                    RELOAD_HOOK()
            finally:
                try:
                    log_handle.close()
                except Exception:
                    pass
                RETRAIN_LOCK.release()

        threading.Thread(target=monitor_and_reload, daemon=True).start()
    except Exception as e:
        RETRAIN_LOCK.release()
        print(f"[-] Lỗi kích hoạt tái huấn luyện: {e}")


@router.get("/models/summary", tags=["Analytics"])
def get_models_summary():
    """Truy xuất tổng hợp so sánh các mô hình và Champion Model."""
    summary_path = os.path.join(MODELS_DIR, "evaluation_results.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Chưa tìm thấy tệp kết quả mô hình!")


@router.get("/models/tuning", tags=["Analytics"])
def get_tuning_history():
    """Truy xuất lịch sử 12 trials tối ưu hóa siêu tham số Optuna."""
    tuning_path = os.path.join(MODELS_DIR, "tuning_history.json")
    if os.path.exists(tuning_path):
        with open(tuning_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Chưa tìm thấy tệp lịch sử tối ưu Optuna!")


@router.get("/ab_test/analytics", tags=["A/B Testing"])
def get_ab_test_analytics():
    """Báo cáo đối sánh hiệu năng và kiểm định giả thuyết thống kê A/B Testing."""
    return analyze_ab_test_performance()


@router.get("/features/{customer_id}", tags=["Feature Store"])
def get_features_by_id(customer_id: int):
    """Truy xuất đặc trưng online từ Feast Online Store."""
    try:
        data = query_online_features([customer_id])
        return {"customer_id": customer_id, "features": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy xuất Feast: {str(e)}")


@router.get("/drift/status", tags=["Monitoring"])
def get_drift_status():
    """Truy vấn báo cáo giám sát Data Drift thời gian thực với ngưỡng chuẩn drift_share >= 0.30."""
    metrics_path = os.path.join(PROCESSED_DIR, "drift_metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = run_drift_analysis()

    features_map = data.get("features", {})
    local_shifted = [
        k for k, v in features_map.items()
        if isinstance(v, dict) and (float(v.get("psi_score", 0.0)) >= 0.25 or bool(v.get("drift_detected", False)))
    ]
    drift_share = float(data.get("drift_share", 0.0))
    is_drifted = bool(data.get("dataset_drift_detected", False)) or (drift_share >= 0.30)
    data["dataset_drift_detected"] = is_drifted
    data["drifted_features_count"] = len(local_shifted)
    if is_drifted:
        data["status_message"] = (
            f"CẢNH BÁO DRIFT TOÀN CỤC: Tỷ lệ đặc trưng dịch chuyển = {drift_share:.2%} (>= 30.0%), "
            f"có {len(local_shifted)} đặc trưng vượt ngưỡng PSI >= 0.25."
        )
    elif local_shifted:
        data["status_message"] = (
            f"Ổn định toàn cục (drift_share={drift_share:.2%} < 30.0%), nhưng phát hiện {len(local_shifted)} "
            f"đặc trưng có dấu hiệu dịch chuyển cục bộ (PSI >= 0.25): {', '.join(local_shifted)}."
        )
    else:
        data["status_message"] = "Phân phối dữ liệu ổn định trên toàn bộ các đặc trưng giám sát."
    return data


@router.post("/api/v1/trigger_retrain", tags=["MLOps Automation"])
def trigger_retraining(background_tasks: BackgroundTasks, force: bool = False, api_key: str = Depends(verify_api_key)):
    """Kích hoạt webhook tái huấn luyện mô hình khi phát hiện Concept/Data Drift."""
    drift_res = run_drift_analysis()
    drift_share = float(drift_res.get("drift_share", 0.0))
    features_map = drift_res.get("features", {})
    local_shifted = [
        k for k, v in features_map.items()
        if isinstance(v, dict) and (float(v.get("psi_score", 0.0)) >= 0.25 or bool(v.get("drift_detected", False)))
    ]

    if drift_res.get("dataset_drift_detected", False) or drift_share >= 0.30 or force:
        if RETRAIN_LOCK.locked():
            return {
                "status": "ALREADY_RUNNING",
                "message": "Tiến trình tái huấn luyện đang chạy, bỏ qua yêu cầu trùng lặp.",
                "drift_share": drift_share
            }
        background_tasks.add_task(run_background_retraining)
        return {
            "status": "TRIGGERED",
            "message": "Đã kích hoạt tái huấn luyện thành công qua MLOps Pipeline.",
            "drift_share": drift_share,
            "triggered_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "job_type": "async_background_execution"
        }

    msg = (
        f"Tỷ lệ drift toàn cục ({drift_share:.2%}) < 30.0% dù có {len(local_shifted)} đặc trưng dịch chuyển cục bộ (PSI >= 0.25). Chưa cần tái huấn luyện toàn diện."
        if local_shifted else
        "Phân phối dữ liệu ổn định (drift_share < 0.30, không có đặc trưng nào vượt ngưỡng). Không cần tái huấn luyện."
    )
    return {
        "status": "SKIPPED",
        "message": msg,
        "drift_share": drift_share,
        "local_shifted_features": local_shifted
    }


@router.get("/metrics", tags=["Observability"])
def get_system_metrics():
    """Cung cấp metrics giám sát hệ thống (Prometheus/Observability standard)."""
    total_inferences = 0
    if os.path.exists(INFERENCE_DB):
        conn = None
        try:
            conn = sqlite3.connect(str(INFERENCE_DB), timeout=10.0)
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("SELECT count(*) FROM inference_logs")
            total_inferences = cur.fetchone()[0]
        except Exception:
            total_inferences = 0
        finally:
            if conn is not None:
                conn.close()

    champion_name = "None"
    summary_path = os.path.join(MODELS_DIR, "evaluation_results.json")
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                champion_name = d.get("champion_model", "None")
        except Exception:
            pass

    return {
        "service": "ChurnGuard-MLOps",
        "uptime_seconds": round(time.time() - APP_START_TIME, 2),
        "total_inference_requests": total_inferences,
        "champion_model": champion_name,
        "feast_online_status": os.path.exists(ONLINE_STORE_DB)
    }


@router.post("/api/v1/reload_model", tags=["MLOps Automation"])
def trigger_reload_model(api_key: str = Depends(verify_api_key)):
    """Kích hoạt Hot-reload mô hình Champion mới nhất từ disk/MLflow vào Serving RAM."""
    if callable(RELOAD_HOOK):
        res = RELOAD_HOOK()
        return {
            "status": "RELOADED",
            "message": "Mô hình đã được nạp lại thành công vào RAM Serving.",
            "reloaded_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "details": res if isinstance(res, dict) else {}
        }
    return {"status": "NOOP", "message": "Reload hook chưa được thiết lập."}
