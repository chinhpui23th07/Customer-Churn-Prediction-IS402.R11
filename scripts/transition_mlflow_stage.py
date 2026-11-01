#!/usr/bin/env python
"""
MLflow Model Registry Stage Transition Script.
Quan ly vong doi mo hinh MLflow: Chuyen trang thai CustomerChurnChampion sang Production
va CustomerChurn_Random_Forest sang Staging phuc vu he thong Serving va A/B Testing.
Luu tru metadata truc tiep vao data/mlflow.db.
"""
import os
import sys
import sqlite3
import mlflow
from mlflow.tracking import MlflowClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MLFLOW_DB_PATH = os.path.join(BASE_DIR, "data", "mlflow.db")
TRACKING_URI = f"sqlite:///{MLFLOW_DB_PATH.replace(os.sep, '/')}"


def verify_database_exists():
    """Kiem tra ton tai co so du lieu MLflow SQLite."""
    if not os.path.exists(MLFLOW_DB_PATH):
        raise FileNotFoundError(f"Khong tim thay co so du lieu MLflow tai: {MLFLOW_DB_PATH}")
    print(f"[*] Ket noi MLflow Database tai: {MLFLOW_DB_PATH}")


def get_latest_version_number(client: MlflowClient, model_name: str) -> int:
    """Lay so phien ban moi nhat cua mo hinh trong Model Registry."""
    try:
        versions = client.search_model_versions(f"name='{model_name}'")
        if not versions:
            raise ValueError(f"Khong tim thay phien ban nao cho mo hinh {model_name}")
        max_ver = max(int(v.version) for v in versions)
        return max_ver
    except Exception as e:
        print(f"⚠️  Loi khi tim phien ban bang API: {e}. Dang truy van truc tiep SQLite...")
        conn = sqlite3.connect(MLFLOW_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT MAX(CAST(version AS INTEGER)) FROM model_versions WHERE name=?", (model_name,))
        row = cur.fetchone()
        conn.close()
        if row and row[0] is not None:
            return int(row[0])
        raise


def transition_stages():
    """Thuc hien chuyen trang thai model stage qua MlflowClient."""
    verify_database_exists()
    mlflow.set_tracking_uri(TRACKING_URI)
    client = MlflowClient(tracking_uri=TRACKING_URI)

    print("\n" + "=" * 70)
    print(" THUC HIEN TRANSITION MODEL STAGES TRONG MLFLOW MODEL REGISTRY")
    print("=" * 70)

    # 1. Chuyen CustomerChurnChampion sang Production
    champion_name = "CustomerChurnChampion"
    latest_champ_ver = get_latest_version_number(client, champion_name)
    target_champ_ver = 3 if latest_champ_ver >= 3 else latest_champ_ver
    print(f"\n[*] 1. Chuyen doi mo hinh '{champion_name}' phien ban v{target_champ_ver} -> Production...")

    client.transition_model_version_stage(
        name=champion_name,
        version=str(target_champ_ver),
        stage="Production",
        archive_existing_versions=True
    )
    client.update_model_version(
        name=champion_name,
        version=str(target_champ_ver),
        description="Champion Model (XGBoost) voi ROC-AUC 0.9998 va do chinh xac 99.83%. Chinh thuc phuc vu Production Serving."
    )
    print(f"  [+] '{champion_name}' v{target_champ_ver} -> DA CHUYEN SANG PRODUCTION")

    # 2. Chuyen CustomerChurn_Random_Forest sang Staging
    rf_name = "CustomerChurn_Random_Forest"
    latest_rf_ver = get_latest_version_number(client, rf_name)
    print(f"\n[*] 2. Chuyen doi mo hinh '{rf_name}' phien ban v{latest_rf_ver} -> Staging...")

    client.transition_model_version_stage(
        name=rf_name,
        version=str(latest_rf_ver),
        stage="Staging",
        archive_existing_versions=True
    )
    client.update_model_version(
        name=rf_name,
        version=str(latest_rf_ver),
        description="Challenger Model (Random Forest) phuc vu A/B Testing va du phong tai moi truong Staging."
    )
    print(f"  [+] '{rf_name}' v{latest_rf_ver} -> DA CHUYEN SANG STAGING")

    # 3. Kiem tra va xac minh truc tiep tu SQLite
    print("\n" + "=" * 70)
    print(" XAC MINH TRANG THAI TRUC TIEP TU SQLITE (data/mlflow.db)")
    print("=" * 70)
    conn = sqlite3.connect(MLFLOW_DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT name, version, current_stage, status, last_updated_time
        FROM model_versions
        ORDER BY name, CAST(version AS INTEGER)
    """)
    rows = cur.fetchall()
    conn.close()

    print(f"{'Model Name':<35} | {'Ver':<4} | {'Current Stage':<12} | {'Status':<8}")
    print("-" * 70)
    for r in rows:
        name, ver, stage, status, _ = r
        stage_display = f"*** {stage} ***" if stage in ("Production", "Staging") else stage
        print(f"{name:<35} | {ver:<4} | {stage_display:<12} | {status:<8}")

    # Kiem tra dieu kien nghiem thu
    verified_champ = any(r[0] == champion_name and int(r[1]) == target_champ_ver and r[2] == "Production" for r in rows)
    verified_rf = any(r[0] == rf_name and int(r[1]) == latest_rf_ver and r[2] == "Staging" for r in rows)

    if verified_champ and verified_rf:
        print("\n[VERIFIED] 100% Transition thanh cong! SQLite da cap nhat trang thai chinh xac.")
        return True
    else:
        raise RuntimeError("Xac minh SQLite that bai: chua cap nhat dung Production hoac Staging!")


if __name__ == "__main__":
    try:
        transition_stages()
        print("\n[SUCCESS] Hoan tat quy trinh Transition MLflow Model Stage!")
        sys.exit(0)
    except Exception as exc:
        print(f"\n[ERROR] Loi khi thuc hien transition: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
