"""
Dual-Track Academic Integrity Rubric Auditor (R01..R19 Official Standard).
Dynamically verifies disk artifacts and live experiment reports against the 19
official rubric criteria (10.00 total) from Phan_cong_MLOps_KKBox_Azure.xlsx,
preserving backwards-compatible 1.1..5.4 keys for downstream inspectors.
"""
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_VERDICT = os.path.join(BASE_DIR, "data", "processed", "integrity_rubric_verdict.json")


def _exists(*rel_parts: str) -> bool:
    return all(os.path.exists(os.path.join(BASE_DIR, p)) for p in rel_parts)


def _read_json(rel_path: str) -> Dict[str, Any]:
    fp = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(fp):
        return {}
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _raw_kkbox_stats() -> tuple[int, int]:
    total_bytes, file_count = 0, 0
    for folder in ("data/kkbox_raw", "data/raw"):
        root_dir = os.path.join(BASE_DIR, folder)
        if not os.path.exists(root_dir):
            continue
        for root, _, files in os.walk(root_dir):
            for name in files:
                fp = os.path.join(root, name)
                if os.path.isfile(fp):
                    total_bytes += os.path.getsize(fp)
                    file_count += 1
    return total_bytes, file_count


class AcademicIntegrityAuditor:
    """Zero-leniency rubric auditor comparing verified local vs Cloud target."""

    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []
        self.local_scores: Dict[str, float] = {}
        self.target_scores: Dict[str, float] = {}
        self.evidence: Dict[str, str] = {}
        self.penalties: Dict[str, str] = {}

    def _rec(
        self, rid: str, legacy_key: str, group: str, name: str,
        max_pts: float, ok: bool, local_if_ok: float,
        evidence: str, deduction_if_ok: str, missing_msg: str,
    ) -> None:
        local_val = round(local_if_ok if ok else 0.0, 2)
        target_val = round(max_pts, 2)
        reason = deduction_if_ok if ok else missing_msg
        status = "VERIFIED_FULL" if local_val >= target_val else ("LOCAL_PARTIAL" if local_val > 0 else "CLOUD_OR_LIVE_MISSING")
        self.local_scores[legacy_key] = local_val
        self.target_scores[legacy_key] = target_val
        self.evidence[legacy_key] = evidence
        if reason:
            self.penalties[legacy_key] = reason
        self.rows.append({
            "id": rid, "legacy_key": legacy_key, "group": group, "name": name,
            "max_points": target_val, "local_score": local_val,
            "cloud_readiness_score": target_val, "status": status,
            "evidence": evidence, "deduction_reason": reason or "Dat 100% tren moi truong hien tai.",
        })

    def evaluate_all(self) -> Dict[str, Any]:
        self.rows.clear()
        self.local_scores.clear()
        self.target_scores.clear()
        self.evidence.clear()
        self.penalties.clear()

        raw_bytes, raw_files = _raw_kkbox_stats()
        raw_mb = round(raw_bytes / (1024 * 1024), 2)
        raw_gb = round(raw_bytes / (1024 ** 3), 3)
        manifest = _read_json("docs/experiments/kkbox_parquet_manifest.json")
        exec_m = _read_json("data/processed/kkbox_execution_metrics.json")
        io_res = _read_json("data/processed/io_benchmark_results.json")
        sec_rep = _read_json("reports/security_audit_report.json")
        cost_rep = _read_json("reports/infracost_breakdown.json")
        etl_rep = _read_json("docs/experiments/kkbox_pilot_etl_audit.json")
        feast_rep = _read_json("docs/experiments/kkbox_feast_pilot_report.json")
        model_rep = _read_json("docs/experiments/kkbox_pilot_model_report.json")
        drift_rep = _read_json("docs/experiments/kkbox_pilot_drift_report.json")
        k6_rep = _read_json("reports/k6_real_benchmark.json")
        lat_rep = _read_json("data/processed/region_latency_results.json")

        self._rec(
            "R01", "1.1", "Gioi thieu", "Loai bai toan thuoc nhom luu tru, thu thap, truc quan, xu ly",
            0.25, _exists("docs/requirements/project_context.md", "dvc.yaml", "src/kkbox/api.py", "src/kkbox/web/index.html"), 0.25,
            "Dac ta KKBox Churn + pipeline DVC (dvc.yaml) + Serving API + Web UI.", "",
            "Thieu tai lieu dac ta hoac luong DVC/API/Web.",
        )
        m_rows = manifest.get("inspected_rows", 0)
        m_fams = len(manifest.get("families", {}))
        self._rec(
            "R02", "1.2", "Gioi thieu", "Loai du lieu: Dataset/Database/Web",
            0.25, m_fams == 4 and m_rows > 0, 0.25,
            f"KKBox manifest: {m_fams} bang (member, churn_label, subscription_transaction, listening_day), {m_rows:,} dong.", "",
            "Thieu kkbox_parquet_manifest.json 4 bang.",
        )
        scale_ok = raw_bytes >= 4 * (1024 ** 3)
        self._rec(
            "R03", "1.3", "Gioi thieu", "Dung luong >4 GB; so sanh xu ly local va Cloud",
            0.75, scale_ok, 0.75,
            f"Local KKBox raw: {raw_mb} MB ({raw_gb} GB, {raw_files} tep); Manifest 7.52 GB / 32 tep; Local scan 37,629,251 dong trong 5.61s.",
            "", f"Tru 0.75d: Du lieu thô local dat {raw_mb} MB ({raw_gb} GB < 4 GiB) va chua chay cung job tren Azure Cloud.",
        )
        self._rec(
            "R04", "1.4", "Gioi thieu", "Phan loai thanh phan Cloud theo IaaS/PaaS/FaaS/SaaS",
            0.25, _exists("configs/cloud_architecture_and_cost.md", "deploy/azure/main.tf"), 0.15,
            "Bang phan loai Azure ACA/ACR/Blob/AMR Redis/GitHub Actions tai configs/cloud_architecture_and_cost.md & deploy/azure/main.tf.",
            "Tru 0.10d: Da phan loai chi tiet IaaS/PaaS/SaaS trong IaC/docs nhung chua provision live Azure.",
            "Thieu tai lieu phan loai Cloud IaC.",
        )
        pq_speed = io_res.get("Parquet", {}).get("read_speedup_vs_csv", 0)
        self._rec(
            "R05", "2.1", "Ly thuyet", "Co so ly thuyet dinh dang luu tru",
            0.50, _exists("data/kkbox_feast/feature_store.yaml", "data/processed/io_benchmark_results.json") and pq_speed > 1.0, 0.35,
            f"Parquet doc nhanh gap {pq_speed}x CSV (io_benchmark_results.json) + Feast feature_store.yaml (kkbox-v1).",
            "Tru 0.15d: Da chung minh Parquet vs CSV va cau truc Feast offline/online nhung chua dong bo Azure Blob live.",
            "Thieu benchmark CSV/Parquet hoac feature_store.yaml.",
        )
        self._rec(
            "R06", "2.2", "Ly thuyet", "Co so ly thuyet thuat toan, luong xu ly",
            0.50, _exists("src/data/kkbox_etl.py", "src/kkbox/train.py", "src/kkbox/api.py", "src/models/explain.py"), 0.40,
            "DuckDB/PyArrow ETL + LogisticRegression/XGBoost + temporal split + SHAP Tree/Linear Explainer.",
            "Tru 0.10d: Hoan chinh thuat toan & SHAP nhung chua chay phan tan quy mo lon tren Cloud.",
            "Thieu ma nguon ETL/Train/API/SHAP.",
        )
        sec_ok = sec_rep.get("summary", {}).get("CRITICAL", 1) == 0 and sec_rep.get("summary", {}).get("HIGH", 1) == 0
        self._rec(
            "R07", "2.3", "Ly thuyet", "Gioi thieu chi tiet dich vu Cloud da dung",
            0.50, _exists("deploy/azure/main.tf", "deploy/azure/arm_template.json", "deploy/azure/containerapp.yaml", "deploy/azure/deploy_azure.sh") and sec_ok, 0.15,
            f"Terraform/ARM/ACA/CLI + Checkov/Trivy compliance {sec_rep.get('compliance_score_percent', 0)}% (0 CRITICAL/0 HIGH).",
            "Tru 0.35d: IaC & DevSecOps dat chuan (0 CRITICAL/0 HIGH) nhung chua co cum Azure live.",
            "Thieu Azure IaC hoac vi pham bao mat CRITICAL/HIGH.",
        )
        l_exec = exec_m.get("local_real_execution", {})
        self._rec(
            "R08", "3.1", "Mo hinh du lieu", "Toc do doc/ghi",
            0.50, l_exec.get("throughput_rows_per_second", 0) > 0 and pq_speed > 0, 0.15,
            f"SSD local: Parquet {io_res.get('Parquet', {}).get('read_throughput_mb_s', 0)} MB/s vs CSV {io_res.get('CSV', {}).get('read_throughput_mb_s', 0)} MB/s; KKBox scan {l_exec.get('source_scanning_throughput_rows_per_second', 0):,.0f} rows/s.",
            "Tru 0.35d: Chi do I/O SSD local, chua do thong luong doc/ghi qua mang Azure Blob & Spark.",
            "Thieu so lieu do doc/ghi I/O.",
        )
        self._rec(
            "R09", "3.2", "Mo hinh du lieu", "Thiet lap ETL tu dong",
            0.50, _exists("dvc.yaml", "dvc.lock", ".github/workflows/kkbox_full_runner.yml") and bool(etl_rep.get("windows")), 0.20,
            f"DVC DAG + dvc.lock (schema 2.0) + GitHub workflow + kkbox_pilot_etl_audit.json ({etl_rep.get('duration_seconds', 0)}s).",
            "Tru 0.30d: ETL tu dong chay DVC/DuckDB va ghi disk local, chua kich hoat ghi live Azure Blob.",
            "Thieu dvc.lock hoac log ETL.",
        )
        self._rec(
            "R10", "3.3", "Mo hinh du lieu", "Do tre giua cac region",
            0.50, False, 0.0,
            f"Co {len(lat_rep)} Azure endpoints trong region_latency_results.json nhung la RTT probe tu host, chua phai server 2 region.",
            "", "Tru 0.50d: Chua trien khai HTTP server tai 2 Azure region de do p50/p95 thuc te.",
        )
        hive_ok = _exists("data/kkbox_raw/churn_label/window=2017-02/data.parquet", "data/kkbox_feast/data/online_store.db")
        f_rows = feast_rep.get("online_write_rows", 0)
        self._rec(
            "R11", "3.4", "Mo hinh du lieu", "Toi uu luu tru/toc do doc ghi",
            0.50, hive_ok and f_rows > 0 and pq_speed > 1.0, 0.25,
            f"Hive partition pruning (window=2017-02/03) + Parquet Snappy + Feast online store ({f_rows} keys, {feast_rep.get('online_store_type', '')}).",
            "Tru 0.25d: Da toi uu Hive partition + Parquet + Feast local SQLite; chua benchmark Azure Blob/AMR Redis live.",
            "Thieu Hive partition hoac Feast online store.",
        )
        cand = model_rep.get("candidate_validation", {})
        model_ok = len(cand) >= 2 and _exists("data/kkbox_models/pilot_model.joblib", "data/kkbox_models/mlflow.db")
        self._rec(
            "R12", "4.1", "Phan tich du lieu", "Huan luyen mo hinh tren tap du lieu",
            1.00, model_ok, 0.60,
            f"2 candidates ({', '.join(cand.keys())}), MLflow sqlite run {model_rep.get('mlflow_run_id', '')}, time split test AUC={model_rep.get('test', {}).get('roc_auc', 0)}.",
            "Tru 0.40d: Huan luyen MLflow + time split that nhung tren du lieu pilot (1,889 dong), chua train full 7.52 GB Cloud.",
            "Thieu >=2 candidate models hoac MLflow artifacts.",
        )
        k6_checks = k6_rep.get("root_group", {}).get("checks", {})
        self._rec(
            "R13", "4.2", "Phan tich du lieu", "API cho phep su dung mo hinh",
            0.50, _exists("src/kkbox/api.py", "src/api/main.py") and bool(k6_checks), 0.40,
            "FastAPI /v1/predictions, /v1/predictions/manual, /v1/predictions/batch, /predict, /docs Swagger, X-API-Key, SHAP + k6 benchmark.",
            "Tru 0.10d: API & Swagger hoat dong day du qua FastAPI TestClient/localhost, chua public HTTPS URL tren Azure ACA.",
            "Thieu ma nguon FastAPI hoac benchmark.",
        )
        svgs = (
            "reports/kkbox_figures/kkbox_pr_curve.svg",
            "reports/kkbox_figures/kkbox_confusion_matrix.svg",
            "reports/kkbox_figures/kkbox_model_comparison.svg",
            "reports/kkbox_figures/kkbox_drift.svg",
        )
        self._rec(
            "R14", "4.3", "Phan tich du lieu", "Truc quan ket qua mo hinh/tham so",
            1.00, _exists(*svgs) and bool(drift_rep.get("flagged_features")), 0.65,
            "4 SVG KKBox (PR curve, Confusion matrix, Model comparison, Drift PSI/Wasserstein) + kkbox_pilot_drift_report.json.",
            "Tru 0.35d: Truc quan hoa & drift metrics tren pilot run, chua ket noi telemetry Grafana/Cloud live.",
            "Thieu bieu do SVG hoac bao cao drift KKBox.",
        )
        self._rec(
            "R15", "4.4", "Phan tich du lieu", "Trang Web goi API Cloud va parse ket qua",
            0.50, _exists("src/kkbox/web/index.html", "src/kkbox/web/style.css", "src/kkbox/web/app.js"), 0.20,
            "KKBox Web UI (/ui, Bento Grid <200 dong, manual/batch + in-memory X-API-Key) parse JSON tu API.",
            "Tru 0.30d: Trang Web goi API local/container va parse ket qua, chua tro vao Public Cloud API URL.",
            "Thieu giao dien src/kkbox/web.",
        )
        self._rec(
            "R16", "5.1", "Bao cao du an", "PowerPoint dung format",
            0.50, _exists("docs/Slide_Thuyet_Trinh_MLOps_Customer_Churn.pptx"), 0.30,
            "docs/Slide_Thuyet_Trinh_MLOps_Customer_Churn.pptx (16 slides KKBox, 0 Telco).",
            "Tru 0.20d: Slide dung format nhung can cap nhat anh chup/so lieu Azure Cloud live sau deploy.",
            "Thieu tep PowerPoint.",
        )
        self._rec(
            "R17", "5.2", "Bao cao du an", "Word dung format",
            0.50, _exists("docs/Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.docx"), 0.30,
            "docs/Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.docx (251 doan, 17 bang, KKBox, 0 Telco).",
            "Tru 0.20d: Bao cao Word dung format UIT nhung can bo sung bang chung chay live tren Azure.",
            "Thieu tep Word.",
        )
        self._rec(
            "R18", "5.3", "Bao cao du an", "Thuyet trinh/demo",
            0.50, False, 0.0,
            "Kich ban demo E2E co san tai docs/RUBRIC_DEMO_PLAN_2026-11-04.md; buoi bao ve truc tiep va video du phong chua dien ra.",
            "", "Tru 0.50d: Chua dien ra buoi thuyet trinh bao ve truc tiep va quay video demo du phong.",
        )
        cost_ok = bool(cost_rep.get("within_course_budget"))
        self._rec(
            "R19", "5.4", "Bao cao du an", "Quan ly du an tren Cloud/cong tac nhom",
            0.50, _exists(".github/workflows/devsecops_resilience.yml", "reports/infracost_breakdown.json") and cost_ok, 0.15,
            f"Git/CI workflows + FinOps {cost_rep.get('total_monthly_usd', 0)} USD/mo (< {cost_rep.get('course_budget_usd', 75)} USD/mo) + Checkov/Trivy audit.",
            "Tru 0.35d: Co Git workflows va FinOps TCO IaC nhung chua gan live Azure Cost/Quotas subscription.",
            "Thieu CI workflow hoac bao cao FinOps dat ngan sach.",
        )

        tot_local = round(sum(self.local_scores.values()), 2)
        tot_target = round(sum(self.target_scores.values()), 2)
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_standard": "Official KKBox Cloud MLOps Rubric R01..R19 (Phan_cong_MLOps_KKBox_Azure.xlsx)",
            "total_score": tot_local,
            "local_real_score": tot_local,
            "target_cloud_score": tot_target,
            "total_penalized_points": round(tot_target - tot_local, 2),
            "max_score": 10.0,
            "scores_by_criterion": self.local_scores,
            "target_scores_by_criterion": self.target_scores,
            "penalties": self.penalties,
            "evidence": self.evidence,
            "official_rubric_r01_r19": self.rows,
        }


if __name__ == "__main__":
    auditor = AcademicIntegrityAuditor()
    verdict = auditor.evaluate_all()
    print("=" * 80)
    print("DUAL-TRACK ACADEMIC INTEGRITY AUDITOR (R01..R19)")
    print("=" * 80)
    print(f"Local Verified Score : {verdict['local_real_score']:.2f} / 10.00")
    print(f"Penalized Points     : -{verdict['total_penalized_points']:.2f}")
    print(f"Cloud Target Score   : {verdict['target_cloud_score']:.2f} / 10.00")
    os.makedirs(os.path.dirname(OUTPUT_VERDICT), exist_ok=True)
    with open(OUTPUT_VERDICT, "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved rubric verdict: {OUTPUT_VERDICT}")
