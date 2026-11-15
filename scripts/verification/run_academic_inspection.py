"""
Master Orchestrator: Academic Integrity & Dual-Track Rubric Inspection.
Aggregates:
- StubAndIntegrityDetector (anti-mockup & architectural gap audit)
- BigData I/O Inspector (local raw size vs >= 4 GiB requirement)
- AcademicIntegrityAuditor (19 official R01..R19 criteria from Excel rubric)
Outputs docs/ACADEMIC_INTEGRITY_AUDIT_REPORT.md and academic_inspection_verdict.json.
"""
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT_VERIF_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_VERIF_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_VERIF_DIR)

from bigdata_io_inspector import audit_current_dataset_size
from integrity_rubric_checker import AcademicIntegrityAuditor
from stub_detector import StubAndIntegrityDetector

OUTPUT_MD = os.path.join(BASE_DIR, "docs", "ACADEMIC_INTEGRITY_AUDIT_REPORT.md")
OUTPUT_JSON = os.path.join(BASE_DIR, "data", "processed", "academic_inspection_verdict.json")


def _format_r01_r19_table(rows: list[dict]) -> str:
    header = (
        "| Ma | Nhom | Tieu chi danh gia | Max | Local | Cloud | Ly do tru diem & Bang chung |\n"
        "| :---: | :--- | :--- | :---: | :---: | :---: | :--- |"
    )
    lines = [header]
    for r in rows:
        reason = r.get("deduction_reason", "").replace("$", "\\$").replace("|", "/")
        ev = r.get("evidence", "").replace("$", "\\$").replace("|", "/")
        detail = f"{ev} - {reason}" if reason else ev
        lines.append(
            f"| **{r['id']}** | {r['group']} | {r['name']} | {r['max_points']:.2f} | "
            f"**{r['local_score']:.2f}** | {r['cloud_readiness_score']:.2f} | {detail} |"
        )
    return "\n".join(lines)


def run_full_inspection() -> dict:
    print("=" * 80)
    print("DUAL-TRACK ACADEMIC INTEGRITY INSPECTION (KKBOX MLOPS)")
    print("=" * 80)

    print("[1/3] Running Stub & Architectural Gap Detector...")
    stub_report = StubAndIntegrityDetector().run_all_audits()
    print(f"      -> {stub_report['critical_violations']} CRITICAL, {stub_report['warnings']} WARNING")

    print("[2/3] Auditing raw dataset volume against >= 4 GiB Cloud scale...")
    size_audit = audit_current_dataset_size()
    print(f"      -> Local raw: {size_audit['total_raw_mb']} MB ({size_audit['total_raw_gb']} GB)")
    print(f"      -> >=4 GiB compliant locally: {size_audit['is_compliant_4gb']}")

    print("[3/3] Scoring 19 official rubric criteria (R01..R19)...")
    rubric_verdict = AcademicIntegrityAuditor().evaluate_all()
    print(f"      -> Local Verified: {rubric_verdict['local_real_score']:.2f} / 10.00")
    print(f"      -> Cloud Target  : {rubric_verdict['target_cloud_score']:.2f} / 10.00")

    master_verdict = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "real_academic_score": rubric_verdict["local_real_score"],
        "target_cloud_score": rubric_verdict["target_cloud_score"],
        "max_score": 10.0,
        "penalized_points": rubric_verdict["total_penalized_points"],
        "data_size_audit": size_audit,
        "stub_detector_audit": stub_report,
        "rubric_breakdown": rubric_verdict,
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(master_verdict, f, indent=2, ensure_ascii=False)

    table_md = _format_r01_r19_table(rubric_verdict["official_rubric_r01_r19"])
    md_content = f"""# BAO CAO THANH TRA DOC LAP VA KIEM DINH LIEM CHINH HOC THUAT (KKBOX MLOPS)

> **Thoi diem thanh tra:** {master_verdict['timestamp']}  
> **Chuan cham diem:** {rubric_verdict['audit_standard']}  
> **Diem thuc te Local:** **{rubric_verdict['local_real_score']:.2f} / 10.00** (Tru **{rubric_verdict['total_penalized_points']:.2f} diem** do thieu live Azure Cloud, du lieu >= 4 GiB va buoi bao ve truc tiep)  
> **Diem muc tieu Cloud (Sau deploy):** **{rubric_verdict['target_cloud_score']:.2f} / 10.00**

---

## 1. TONG QUAN KET LUAN THANH TRA

He thong KKBox Customer Churn MLOps tren local da hoan thien ma nguon, ETL DuckDB (`src/data/kkbox_etl.py`), 12 dac trung `kkbox-v1`, huan luyen pilot (`LogisticRegression` va `XGBoost`, MLflow SQLite), Feast (`data/kkbox_feast/`), FastAPI Serving (`src/kkbox/api.py`, `src/api/main.py`), Drift Normalized Wasserstein + PSI (`src/monitoring/drift_detector.py`), Azure IaC (`deploy/azure/`) va FinOps `\\$70.61/mo` (< nguong `\\$75.00/mo`).

Cac khoang trong thuc thi can hoan tat de dat tron ven muc tieu Cloud:

1. **Quy mo du lieu local (`R03`):** Tong du lieu tho local (`data/kkbox_raw/` + `data/raw/`) la **{size_audit['total_raw_mb']} MB ({size_audit['total_raw_gb']} GB)**, chua dat nguong >= 4 GiB va chua chay cung job tren Azure Cloud so voi manifest KKBox 7.52 GB (`442,211,685` dong, 32 tep Parquet).
2. **Ha tang Azure Cloud (`R07`, `R09`, `R10`, `R11`, `R15`, `R19`):** IaC Terraform/ARM/ACA va FinOps (`\\$70.61/mo`) da san sang (Checkov/Trivy 0 CRITICAL / 0 HIGH), nhung chua provision live subscription, Blob Storage, Azure Managed Redis (`Balanced_B0`) hoac server HTTP tai 2 Azure region.
3. **Thuyet trinh & demo truc tiep (`R18`):** Kich ban demo da co san, nhung buoi bao ve truc tiep va video du phong chua duoc thuc hien.

---

## 2. BANG DIEM CHI TIET 19 TIEU CHI CHINH THUC (R01..R19)

{table_md}
| **TONG** | - | **DIEM TOAN HE THONG** | **10.00** | **{rubric_verdict['local_real_score']:.2f}** | **{rubric_verdict['target_cloud_score']:.2f}** | **TRU {rubric_verdict['total_penalized_points']:.2f} DIEM KHI CHUA DEPLOY AZURE LIVE** |

---

## 3. PHAT HIEN STUB / ARCHITECTURAL GAPS

```json
{json.dumps(stub_report['findings'], indent=2, ensure_ascii=False)}
```
"""

    os.makedirs(os.path.dirname(OUTPUT_MD), exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[+] Exported Markdown Report: {OUTPUT_MD}")
    print(f"[+] Exported JSON Verdict   : {OUTPUT_JSON}")
    return master_verdict


if __name__ == "__main__":
    run_full_inspection()
