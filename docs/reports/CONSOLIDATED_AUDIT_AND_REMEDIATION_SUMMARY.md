# Consolidated Audit and Remediation Summary (Local Hardening)

> **Platform:** ChurnGuard MLOps Level 2 Enterprise Platform
> **Author:** [Để trống / Tác giả bảo mật] | **Scientific Advisor:** ThS. Hà Lê Hoài Trung
> **Scope:** Local source, IaC, FinOps, data integrity, DevSecOps, and documentation remediation (`git push` strictly disabled per request)

---

## 1. Executive Verification Summary

| Verification Gate | Command / Script | Observed Post-Edit Result | Status |
| :--- | :--- | :--- | :---: |
| **Full Automated Test Suite** | `python -m pytest tests/ -v` | `211 passed, 1 skipped` (`test_testcontainers_live_container` skipped cleanly when local Docker daemon is unavailable; `57.86s`) | PASS |
| **400-Line Modularity Cap** | `python scripts/verification/audit_line_cap.py` | `81/81` files `<= 400` lines (`0` violations; top file `390` lines, `src/api/main.py` at `340` lines <= `370`) | PASS |
| **Presentation Component Cap** | `python scripts/verification/verify_report_evidence.py` | `5/5` files in `src/web/` `< 200` lines (`app.js`: 197, `charts.js`: 157, `dashboard.py`: 183, `index.html`: 181, `style.css`: 172) | PASS |
| **Truth, Dash & PII Audit** | `python scripts/verification/verify_truth_doc.py` | `0` Unicode em/en dashes, `0` student PII matches, author marker + advisor intact | PASS |
| **Domain Semantic Integrity** | `python scripts/verification/assert_domain_semantic_integrity.py` | `100%` single-domain compliance across `src/` and `scripts/` | PASS |
| **Stub & Architecture Audit** | `python scripts/verification/stub_detector.py` | `1` expected local finding only (`data/feast_repo/feature_store.yaml` uses `sqlite` fallback when live remote Redis is offline) | VERIFIED |
| **IaC & Security Baseline** | `reports/checkov_real_report.json` & `reports/security_audit_report.json` | Checkov `28/28` passed (`18` Terraform, `10` ARM); Security Audit `97.25%` (`177/182` rules passed, `0 CRITICAL`, `0 HIGH`) | PASS |
| **Academic Deliverables** | `scripts/generate_docx_report.py` & `scripts/generate_pptx_slides.py` | Regenerated 31-page UIT DOCX/PDF report and 16:9 PPTX slide deck with visual verification on Tables 5.3-5.5 | PASS |

---

## 2. Remediated Workstreams (Local Changes Only)

### 2.1. Security, API Hardening & Compliance
- Enforced `hmac.compare_digest` timing-safe API key verification and role separation for `POST /v1/model/reload` and `POST /api/v1/trigger_retrain`.
- Tightened `src/api/main.py` cleanly below 370 lines (`340` lines) without relaxing `tests/test_shap_batch_optimization.py::test_source_code_line_caps`.
- Verified non-root container execution in `Dockerfile` (`appuser`), Azurite dynamic env credentials (`src/resilience/azurite_adapter.py`), and `97.25%` compliance (`0 CRITICAL`, `0 HIGH`) in [security_audit_report.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/reports/security_audit_report.json).

### 2.2. KKBox Primary Big Data & Benchmark Lineage Parity
- Standardized the primary dataset hierarchy across code contracts, API docs, thesis chapters, slides, and truth catalogs: **KKBox Subscriber Retention Intelligence** (`7.52 GB` / `32` Parquet Zstd files / `442,211,685` source rows, DuckDB bounded memory `<= 2 GB` Radix disk spilling scanning `37,629,251` -> `970,960` entities in `5.61s`).
- Highlighted primary production champion metrics from [kkbox_evaluation_results.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/data/models/kkbox_evaluation_results.json): `KKBox_LGBM_Champion` (`ROC-AUC = 0.8764`, `PR-AUC = 0.5947`, `Accuracy = 0.9331`, `Brier = 0.05312`), alongside the preserved `442,211`-row legacy regression benchmark (`XGBoost ROC-AUC = 0.9990`).
- Updated [verify_report_evidence.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/verification/verify_report_evidence.py) so it verifies against [kkbox_parquet_manifest.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/experiments/kkbox_parquet_manifest.json) when pruned legacy raw CSVs are not stored locally.

### 2.3. Cloud IaC & 6-Provider FinOps Calibration
- Synchronized [infracost_breakdown.json](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/reports/infracost_breakdown.json), [cloud_architecture_and_cost.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/configs/cloud_architecture_and_cost.md), [uit_report_ch5.py](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/scripts/uit_report_ch5.py), [MASTER_PROJECT_TECHNICAL_HANDBOOK.md](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/specifications/MASTER_PROJECT_TECHNICAL_HANDBOOK.md), and all specification docs:
  - **Azure Terraform IaC Baseline:** `$70.61/month` (Container Apps `$46.80`, Azure Managed Redis Balanced B0 TLS Port `10000` `$12.00`, ACR Basic `$5.00`, Log Analytics `$4.41`, Storage LRS `$2.40`).
  - **Serverless Scale-to-Zero Target Workload:** `$11.22/month` (vs `$176.96/month` 24/7 peak load, staying well below `< $75.00/month` target cap).
  - **Multi-Cloud Evidence Benchmark:** Covers Microsoft Azure, AWS (`m6i.xlarge`, `t4g.xlarge`, Fargate), GCP (`e2-standard-4`, Cloud Run), OCI (`VM.Standard3.Flex` `$91.54/mo`), OVHcloud (`Rise-1` `$120.00/mo`), and Viettel IDC (`$177.16/mo`).

### 2.4. Anonymization, Typography & Repository Hygiene
- Removed leftover student PII (`[Author Redacted]` / `[Để trống / Tác giả bảo mật]`), course-only framing, fabricated decree strings, ungrounded `O(1)` memory claims, and Unicode em/en dashes across all markdown docs, thesis scripts, PPTX deck, and metadata.
- Confirmed zero changes pushed to GitHub (`git push` not invoked).
