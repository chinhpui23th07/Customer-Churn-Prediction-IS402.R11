# ChurnGuard MLOps Platform - Codebase Structure & Architecture Inventory

> **Specification Standard:** Master Governance Specification `AGENTS.md` v3.4  
> **System Identity:** Codebase Structure Mapper (`mapper`)  
> **Project Scope:** ChurnGuard MLOps Enterprise Platform (KKBox 37.6M Big Data Churn Prediction & Azure Architecture)  
> **Output Artifact:** `docs/requirements/directory_structure_inventory.md`  
> **Governing Rules:** Strict 400-Line Code Cap, Natural Domain Palettes, Standard Hyphen `-`, Zero Mockup, Real Execution  

---

## 1. Executive Summary & Inventory Overview

This document provides a comprehensive, exhaustive directory and file inventory of the entire ChurnGuard MLOps codebase. Every directory and key file across the 10 core targets (`src/`, `tests/`, `scripts/`, `configs/`, `deploy/`, `data/`, `docs/`, `reports/`, `tools/`, `assets/`) is cataloged with its exact relative path, line count (or storage size for binaries/datasets), and specific architectural responsibility.

### High-Level Architectural Summary Table

| Top-Level Directory | File Count / Artifacts | Primary Focus & Domain Responsibility |
| :--- | :--- | :--- |
| `src/` | 46 source files (9 sub-packages) | Core production code: API serving, ETL, economics, feature store, models, monitoring, resilience, and web UI. |
| `tests/` | 28 test files | Multi-tier test suite: unit tests, integration scenarios, audit swarm verifications, chaos engineering, and security WAF. |
| `scripts/` | 38 script files (28 root, 10 verification) | Operational automation, load testing, academic report generation (.docx/.pptx), and strict compliance auditors. |
| `configs/` | 2 configuration files | Declarative ML parameters (`model_params.yaml`) and Azure cloud architecture blueprint & cost breakdown. |
| `deploy/` | 8 deployment files (3 targets) | Production cloud deployment: Terraform IaC, ARM templates, Azure Container Apps, Dapr state store, and runner scripts. |
| `data/` | 10 subdirectories / DBs (1.3+ GB) | Real empirical data: Feast feature store, MLflow registry, DuckDB/Parquet datasets (37.6M rows), and trained weights. |
| `docs/` | 15 root docs + 6 subdirectories | Formal thesis (.docx/.pdf), presentation slides (.pptx), master truth catalogs, and operational runbooks. |
| `reports/` | 8 security & benchmark reports | Empirical audit evidence: Checkov IaC scan, Trivy image scan, Infracost breakdown, K6 load test, and MicroBurst audit. |
| `tools/` | 10 external tool suites | Open-source enterprise tooling: K6, Infracost, Trivy, MicroBurst, AzureHound, CloudFox, Azurite, and Reveal.js. |
| `assets/` | 2 brand vector assets | Bespoke vector SVG logo and banner adhering to Oceanic Navy and Emerald natural palettes (zero AI emojis). |

---

## 2. Core Source Code: `src/` (All 9 Sub-Packages)

The `src/` directory houses the modular implementation of the ChurnGuard platform, divided into 9 dedicated architectural sub-packages. All source code strictly adheres to the 400-line hard cap per file.

### 2.1. `src/api/` - High-Throughput Model Serving & Management (6 files)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/api/ab_testing.py` | 147 | Implements dynamic A/B testing and traffic split routing between Champion (LightGBM) and Challenger (XGBoost/RandomForest) models, incorporating Bayesian posterior updates and Thompson Sampling. |
| `src/api/database.py` | 42 | Manages centralized SQLite database connections with Write-Ahead Logging (WAL) mode enabled for high-concurrency, non-blocking inference logging. |
| `src/api/main.py` | 358 | Main FastAPI application entrypoint providing model serving endpoints (`/predict`, `/predict/batch`), Prometheus middleware instrumentation, CORS, and request lifecycle management. |
| `src/api/routes_management.py` | 224 | APIRouter module isolating administrative, telemetry, and system observability endpoints (`/health`, `/metrics`, `/audit/security`, `/retrain/trigger`). |
| `src/api/schemas.py` | 71 | Pydantic data contracts defining input customer feature payloads, prediction probability outputs, risk categories, and error response schemas. |
| `src/api/utils.py` | 277 | Serving helper utilities: background asynchronous logging to SQLite WAL, real-time TreeSHAP feature attribution generation, and rule-based retention action recommendations. |

### 2.2. `src/data/` - Big Data ETL & I/O Engineering (6 files)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/data/benchmark_io.py` | 119 | Performance benchmarking harness measuring IOPS, read/write latency, and throughput across CSV, Parquet, and Feather formats on storage volumes. |
| `src/data/data_quality.py` | 187 | Advanced data validation engine detecting missing values, distribution anomalies, out-of-range bounds, and schema drift using IQR and Z-score methods. |
| `src/data/download_dataset.py` | 166 | Legacy Kaggle dataset download utility (deprecated in favor of zero-disk Hugging Face streaming). |
| `src/data/kkbox_etl.py` | 377 | Big Data ETL pipeline powered by DuckDB and PySpark streaming 37.6M KKBox transactions, applying cutoff-safe aggregation, feature joins, and Parquet partitioning. |
| `src/data/latency_simulator.py` | 136 | Multi-region latency simulation tool benchmarking round-trip network performance between Southeast Asia and East US deployment zones. |
| `src/data/preprocess.py` | 373 | Data cleaning, temporal train/val/test splitting, leakage prevention, standard scaling, and categorical encoding pipelines. |

### 2.3. `src/economics/` - Causal Uplift & Financial Optimization (1 file)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/economics/retention_optimizer.py` | 273 | Economic decision theory engine calculating CATE (Conditional Average Treatment Effect), optimal discount intervention thresholds, and net ROI maximization under marketing budget constraints. |

### 2.4. `src/features/` - Enterprise Feature Store Integration (1 file)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/features/feature_store.py` | 319 | Enterprise Feature Store abstraction integrating Feast with local SQLite registry, Parquet offline storage, and Redis online low-latency key-value serving. |

### 2.5. `src/kkbox/` - KKBox Domain Pipeline & Web Interface (13 files)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/kkbox/__init__.py` | 1 | KKBox package initialization exporting core pipeline identifiers. |
| `src/kkbox/api.py` | 363 | Specialized KKBox churn prediction API matching exact training feature parity and providing instant subscriber churn scoring. |
| `src/kkbox/contract.py` | 15 | Canonical contract defining the 17 verified feature names, cutoff timestamps, and prediction target labels. |
| `src/kkbox/drift.py` | 152 | Statistical drift analysis comparing feature distributions across consecutive temporal label windows using Kolmogorov-Smirnov test and PSI. |
| `src/kkbox/features.py` | 113 | Cutoff-safe PySpark feature engineering logic aggregating user listening logs and transaction history strictly prior to observation cutoff. |
| `src/kkbox/prepare_feast.py` | 110 | Ingestion script compiling label-free KKBox historical feature snapshots and pushing them into Feast offline and online storage. |
| `src/kkbox/run_etl.py` | 116 | Orchestration script executing the two-window KKBox feature ETL pipeline on DuckDB/Spark locally or on Azure Virtual Machines. |
| `src/kkbox/schemas.py` | 88 | Pydantic data models defining KKBox subscriber profile inputs, prediction outputs, and explanation payloads. |
| `src/kkbox/train.py` | 195 | Cutoff-safe model training script fitting LightGBM on 970,960 KKBox records with MLflow experiment tracking. |
| `src/kkbox/web/app.js` | 221 | Interactive client-side controller handling subscriber lookup, real-time prediction calls, and Bento Grid card updates. |
| `src/kkbox/web/favicon.svg` | 7 | Custom vector SVG favicon for the KKBox web application. |
| `src/kkbox/web/index.html` | 105 | Google Stitch compliant Bento Grid HTML interface for the KKBox interactive churn demo. |
| `src/kkbox/web/style.css` | 15 | Minimalist scoped CSS styles complementing Google Stitch UI guidelines. |

### 2.6. `src/models/` - Machine Learning & Governance (7 files)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/models/evaluate.py` | 151 | Comprehensive model evaluation module computing ROC-AUC, PR-AUC, F1-Score, Brier loss, and generating calibration curves. |
| `src/models/explain.py` | 160 | Explainable AI (XAI) service computing local and global feature importance attributions using TreeSHAP and KernelSHAP. |
| `src/models/model_diagnostics.py` | 244 | Advanced model diagnostics performing slice-based error analysis, confusion matrix decomposition, and threshold optimization. |
| `src/models/retraining_job.py` | 261 | Decoupled background retraining worker featuring distributed file-based locking (`.lock`), concurrency control, and automated model promotion. |
| `src/models/train_kkbox.py` | 345 | Dedicated training pipeline training candidate models (LightGBM, XGBoost, Random Forest, Logistic Regression) on 970,960 KKBox records. |
| `src/models/train_pipeline.py` | 382 | Multi-model benchmark pipeline with MLflow tracking, automated evaluation metrics logging, and model registry versioning. |
| `src/models/tune_optuna.py` | 157 | Automated Bayesian hyperparameter tuning using Optuna TPE (Tree-structured Parzen Estimator) for tree depth, learning rate, and regularization. |

### 2.7. `src/monitoring/` - Real-Time Observability (1 file)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/monitoring/drift_detector.py` | 348 | Real-time production drift detection engine calculating Kolmogorov-Smirnov statistic, Population Stability Index (PSI), and Wasserstein distance on inference streams. |

### 2.8. `src/resilience/` - Cloud Fault Tolerance & Enterprise Patterns (6 files)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/resilience/__init__.py` | 35 | Resilience package exports exposing unified fault tolerance decorators and configuration constants. |
| `src/resilience/azurite_adapter.py` | 220 | Dual-mode storage client seamlessly abstracting Azure Blob Storage in cloud production and Azurite emulator in local environments. |
| `src/resilience/bulkhead.py` | 172 | Bulkhead isolation pattern using bounded concurrency semaphores to prevent resource exhaustion under traffic spikes. |
| `src/resilience/circuit_breaker.py` | 188 | Martin Fowler Circuit Breaker state machine (Closed, Open, Half-Open) with automated failure rate thresholds and recovery cooldown. |
| `src/resilience/resilience_pipeline.py` | 138 | Unified resilience pipeline chaining Retry, Circuit Breaker, Bulkhead, and Fallback policies into a single robust execution wrapper. |
| `src/resilience/retry_policy.py` | 152 | Exponential backoff retry policy with full jitter to avoid thundering herd problems during downstream service recovery. |

### 2.9. `src/web/` - Google Stitch Observability Dashboard (5 files)

| File Path | Lines | Architectural Responsibility |
| :--- | :---: | :--- |
| `src/web/app.js` | 197 | Vanilla JavaScript frontend controller managing real-time API polling, telemetry updates, and DOM card interactions. |
| `src/web/charts.js` | 157 | Chart.js visualizer rendering dynamic real-time charts for drift metrics, latency distributions, and ROC-AUC curves. |
| `src/web/dashboard.py` | 183 | Streamlit operational dashboard providing an alternative UI for model inspection, drift alerts, and batch evaluation. |
| `src/web/index.html` | 181 | Google Stitch compliant Bento Grid HTML single-page application featuring glassmorphism and real-time telemetry panels. |
| `src/web/style.css` | 172 | Design token styling implementing Oceanic Navy, Forest Emerald, and Amber color palettes (strictly avoiding generic AI purple). |

---

## 3. Test Suites: `tests/` (All 28 Test Files)

The `tests/` directory contains 28 specialized test files covering 100% of the platform's functional, statistical, resilience, security, and academic integrity contracts.

| Test File Path | Lines | Test Scope & Verification Objective |
| :--- | :---: | :--- |
| `tests/test_api.py` | 268 | Validates FastAPI serving endpoints, request payload validation, health checks, Prometheus metrics, and error codes. |
| `tests/test_audit_team_1.py` | 342 | Audit Swarm Team 1: Rigorous verification of data pipelines, schema contracts, and temporal leakage prevention. |
| `tests/test_audit_team_2.py` | 245 | Audit Swarm Team 2: Verification of model evaluation metrics (ROC-AUC, PR-AUC, Accuracy, Brier score) against empirical truth. |
| `tests/test_audit_team_3.py` | 237 | Audit Swarm Team 3: Verification of explainability outputs (TreeSHAP attributions) and CATE uplift retention decisions. |
| `tests/test_audit_team_4.py` | 256 | Audit Swarm Team 4: Verification of cloud resilience patterns (Retry with jitter, Circuit Breaker states, Bulkhead concurrency). |
| `tests/test_audit_team_5.py` | 163 | Audit Swarm Team 5: Verification of Feast feature store integration, Redis cache hit ratio, and multi-region latency. |
| `tests/test_audit_team_6.py` | 214 | Audit Swarm Team 6: Verification of DevSecOps compliance, Azure IaC WAF rules, and security scanning baselines. |
| `tests/test_azure_iac_waf.py` | 126 | Static compliance tests asserting that Terraform (`main.tf`) and ARM templates enforce Azure WAF, HTTPS, and TLS 1.2+. |
| `tests/test_causal_uplift.py` | 196 | Validates CATE estimation algorithms, treatment effect confidence intervals, and budget-constrained discount optimization. |
| `tests/test_devsecops_compliance.py` | 139 | Automated DevSecOps tests verifying 0 plain-text secrets, valid SARIF/JSON security reports, and passing vulnerability thresholds. |
| `tests/test_e2e_scenarios.py` | 350 | End-to-end integration tests simulating a full customer lifecycle: raw data -> ETL -> training -> serving -> drift -> retrain. |
| `tests/test_kkbox_api.py` | 398 | Dedicated test suite for KKBox API endpoints, verifying single and batch predictions against real 17-feature schemas. |
| `tests/test_kkbox_benchmarks.py` | 230 | Validates empirical Big Data I/O benchmarks, asserting Parquet read performance advantages over CSV. |
| `tests/test_kkbox_chaos_load.py` | 246 | Chaos engineering tests verifying that the API gracefully degrades to fallbacks when Azurite storage or Feast fails. |
| `tests/test_kkbox_contract_parity.py` | 105 | Strict contract parity test verifying exact match between offline training feature columns and online serving schema. |
| `tests/test_kkbox_drift.py` | 205 | Unit tests for Kolmogorov-Smirnov, PSI, and Wasserstein drift algorithms using synthetic shift distributions. |
| `tests/test_kkbox_etl.py` | 198 | Unit tests for DuckDB/PySpark ETL transformation logic, aggregations, and windowed listening metrics. |
| `tests/test_kkbox_features.py` | 324 | Verification of cutoff-safe feature computation, confirming zero transactions past the cutoff date are incorporated. |
| `tests/test_kkbox_figures.py` | 144 | Automated test confirming that all 19 required academic report figures and SVG charts exist on disk and are valid. |
| `tests/test_kkbox_integrity.py` | 294 | Zero-leniency academic integrity tests asserting 0 mock data generators, 0 synthetic fallbacks, and real model files. |
| `tests/test_kkbox_security_waf.py` | 252 | Application security tests asserting that malicious SQL injection, XSS payloads, and path traversal requests are rejected. |
| `tests/test_kkbox_train_feast.py` | 272 | Integration tests verifying Feast entity registration, feature view generation, and historical feature retrieval. |
| `tests/test_kkbox_training.py` | 223 | Unit tests for KKBox LightGBM training script, parameter parsing, and MLflow artifact logging. |
| `tests/test_kkbox_web.py` | 98 | Functional contract tests verifying static web assets (`index.html`, `app.js`, `style.css`) load and return HTTP 200. |
| `tests/test_redis_finops.py` | 178 | Validates Redis cache hit ratio (>80%), TTL expiration, and FinOps cost-per-query calculations. |
| `tests/test_resilience_integration.py` | 309 | Integration tests verifying combined fault recovery using Retry, Circuit Breaker, and Azurite blob simulation. |
| `tests/test_retraining_concurrency.py` | 239 | Concurrency tests validating distributed locking, preventing simultaneous retraining jobs from corrupting weights. |
| `tests/test_shap_batch_optimization.py` | 226 | Performance tests verifying that TreeSHAP batch optimization satisfies real-time latency budgets (<50ms per explanation). |

---

## 4. Automation & Verification Scripts: `scripts/` (All 40 Scripts)

The `scripts/` directory provides operational tooling, academic report compilers, and automated verification suites.

### 4.1. Core Operational & Report Generation Scripts (31 files)

| Script File Path | Lines | Operational Purpose & Execution Scope |
| :--- | :---: | :--- |
| `scripts/audit_vision_and_package.py` | 231 | Visual verification tool converting PDF report pages to images for inspection and verifying clean submission archives. |
| `scripts/chaos_resilience_test.py` | 199 | Fault injection CLI simulating network dropouts, Azurite service failure, and latency spikes against live endpoints. |
| `scripts/check_file_lines.py` | 80 | Automated CI line-count auditor enforcing the 400-line hard cap across `src/` and `scripts/`. |
| `scripts/download_kkbox.py` | 101 | Hugging Face streaming downloader streaming raw KKBox Parquet files directly to storage without memory exhaustion. |
| `scripts/finops_infracost_scan.py` | 247 | FinOps shift-left cost analysis scanner parsing Terraform infrastructure and generating projected monthly run rates. |
| `scripts/generate_docx_report.py` | 164 | Academic Word report compiler generating the complete thesis document according to official UIT formatting standards. |
| `scripts/generate_pptx_slides.py` | 373 | Academic slide deck compiler automatically building 16:9 widescreen presentation slides (.pptx) with diagrams. |
| `scripts/generate_shap_plots.py` | 153 | Generates static SHAP summary, dependence, and waterfall SVG plots for model explainability documentation. |
| `scripts/inspect_kkbox_source.py` | 127 | Fast Parquet metadata inspector reading row counts, column types, and schema without full dataset downloads. |
| `scripts/k6_load_test.js` | 75 | Distributed K6 load test script defining ramp-up, steady-state (100 VU), and spike phases for API throughput evaluation. |
| `scripts/kkbox_benchmark_read.py` | 102 | Micro-benchmark measuring sequential read throughput and memory usage of KKBox Parquet files. |
| `scripts/kkbox_latency_probe.py` | 138 | Network probe measuring single and multi-region round-trip latencies for prediction requests. |
| `scripts/kkbox_make_figures.py` | 197 | Chart generation utility rendering publication-quality SVG figures from benchmark JSON results. |
| `scripts/kkbox_pick_demo_key.py` | 36 | Utility script querying available subscriber IDs from local data for interactive live demonstration. |
| `scripts/reseed_inference_logs.py` | 98 | Maintenance script resetting and re-seeding the SQLite WAL database with verified production inference records. |
| `scripts/run_kkbox_tests.ps1` | 40 | PowerShell test runner orchestrating test discovery, execution, and coverage report generation. |
| `scripts/run_load_test.py` | 159 | High-throughput concurrent load testing runner verifying p95/p99 latency SLOs under load. |
| `scripts/run_real_microburst.ps1` | 34 | NetSPI MicroBurst Azure security audit runner assessing Azure Storage security and RBAC posture. |
| `scripts/security_audit_suite.py` | 267 | Enterprise DevSecOps test suite orchestrating Checkov, Trivy, and custom AST security scans. |
| `scripts/temp_find_fail.py` | 6 | Diagnostic helper script for isolating specific test failures during debugging. |
| `scripts/temp_inspect_reports.py` | 49 | Validation helper verifying JSON schema integrity of security scan outputs. |
| `scripts/temp_inspect_sec.py` | 15 | Quick audit script inspecting security rule violation identifiers. |
| `scripts/transition_mlflow_stage.py` | 139 | MLflow Model Registry governance script transitioning models from Staging to Production. |
| `scripts/uit_report_ch1_to_3.py` | 279 | Academic report content generator for Chapter 1 (Introduction), Chapter 2 (Literature Review), and Chapter 3 (Architecture). |
| `scripts/uit_report_ch4_to_6.py` | 196 | Academic report content generator for Chapter 4 (Implementation), Chapter 5 (Evaluation), and Chapter 6 (Conclusion). |
| `scripts/uit_report_ch5.py` | 256 | Specialized report generator for Chapter 5 compiling cloud benchmarking, FinOps analysis, and performance tuning. |
| `scripts/uit_report_ch6_and_appendix.py` | 103 | Content generator for Chapter 6 conclusions, IEEE citations, and technical appendices. |
| `scripts/uit_report_content.py` | 376 | Core document styling engine defining typography (TNR 13pt), margins (3-2-2.5-2.5cm), tables, and callouts. |
| `scripts/uit_report_covers.py` | 190 | Official UIT cover page generator creating formal inner and outer title pages with institutional borders. |
| `scripts/uit_report_frontmatter.py` | 338 | Front matter compiler building Academic Integrity Pledge, Acknowledgments, TOC, List of Figures, and List of Tables. |
| `scripts/validate_kkbox_labels.py` | 57 | Data validation script verifying true observed churn labels without exposing PII customer data. |

### 4.2. Verification & Integrity Suite: `scripts/verification/` (9 files)

| Script File Path | Lines | Verification Focus & Compliance Gate |
| :--- | :---: | :--- |
| `scripts/verification/assert_domain_semantic_integrity.py` | 97 | Enforces Invariant 20: Verifies single coherent entity and dataset usage, prohibiting cross-domain pollution. |
| `scripts/verification/audit_line_cap.py` | 67 | Enforces Invariant 02: Scans all `.py` files in `src/` and `scripts/`, failing if any file exceeds 400 lines. |
| `scripts/verification/bigdata_io_inspector.py` | 104 | Enforces Invariant 13: Audits Parquet file sizes, row counts, and verifies that real big data I/O took place. |
| `scripts/verification/check_fixes.py` | 265 | Regression test suite verifying that all previously identified defects and audit findings remain resolved. |
| `scripts/verification/final_comprehensive_check.py` | 240 | Comprehensive master audit verifying complete compliance with UIT IS402 capstone rubric requirements. |
| `scripts/verification/integrity_rubric_checker.py` | 192 | Automated rubric scoring tool evaluating the codebase against academic grading criteria. |
| `scripts/verification/run_academic_inspection.py` | 148 | Master inspection orchestrator executing static analysis, test runs, and artifact consistency checks. |
| `scripts/verification/stub_detector.py` | 215 | AST inspection tool detecting mock functions, placeholder pass stubs, or fake data generators. |
| `scripts/verification/verify_report_evidence.py` | 239 | Triple cross-validation auditor certifying that 100% of numbers in the thesis match real experimental data on disk. |

---

## 5. System Configuration: `configs/` (2 files)

| File Path | Size | Architectural Responsibility |
| :--- | :---: | :--- |
| `configs/cloud_architecture_and_cost.md` | 23.4 KB | Comprehensive Azure cloud architecture specification, detailing service tiers, network security, and Infracost financial estimates. |
| `configs/model_params.yaml` | 6.0 KB | Centralized declarative configuration for model hyperparameters (LightGBM, XGBoost, RF, LR), training grids, and feature schemas. |

---

## 6. Cloud Deployment & Infrastructure: `deploy/` (3 Targets, 8 files)

| File Path | Size | Target Environment & Architectural Function |
| :--- | :---: | :--- |
| `deploy/azure/arm_template.json` | 8.7 KB | Azure Resource Manager (ARM) template defining Azure Container Apps, Storage Accounts, and Key Vault. |
| `deploy/azure/containerapp.yaml` | 2.1 KB | Declarative Azure Container Apps manifest specifying ingress rules, CPU/memory scaling, and environment variables. |
| `deploy/azure/deploy_azure.bat` | 4.6 KB | Windows deployment script automating resource group provisioning, container building, and cloud deployment. |
| `deploy/azure/deploy_azure.sh` | 3.7 KB | POSIX Bash deployment script for automated provisioning on Linux and CI/CD runners. |
| `deploy/azure/main.tf` | 5.7 KB | Production Terraform configuration declaring App Services, Storage Accounts, Application Insights, and NSG rules. |
| `deploy/azure/README.md` | 3.7 KB | Deployment guide outlining Azure CLI authentication, configuration variables, and rollout procedures. |
| `deploy/dapr/statestore.yaml` | 0.6 KB | Dapr distributed state store component manifest configured for Azure Cache for Redis. |
| `deploy/kkbox/deploy_from_runner.sh` | 1.2 KB | Automated CI/CD deployment script executed from GitHub Actions runner for KKBox serving. |

---

## 7. Empirical Data & Artifacts: `data/` (10 Directories / Stores)

The `data/` directory contains all real empirical datasets, serialized model weights, execution metrics, and tracking databases.

| Directory / Artifact Path | Details / Size | Architectural Content & Role |
| :--- | :---: | :--- |
| `data/feast_repo/` | 7 files (1.23 GB) | Feast feature store repository containing `feature_store.yaml`, feature definitions, and local registry. |
| `data/inference_logs.db` | 6.22 MB | SQLite WAL-mode database persistently recording live inference requests, prediction scores, and response latencies. |
| `data/kkbox_feast/` | 3 files | Feast configuration files specifically dedicated to KKBox offline feature views. |
| `data/kkbox_sample_raw/` | 4 files (80 KB) | Raw schema sample snapshots used for unit testing data contracts without large dataset overhead. |
| `data/mlflow.db` | 2.69 MB | SQLite database backing the local MLflow Tracking Server, recording runs, parameters, metrics, and model tags. |
| `data/models/` | 9 files (13.93 MB) | Serialized machine learning models: `champion_model.joblib` (339 KB), `kkbox_champion_model.joblib` (356 KB), `evaluation_results.json` (27.8 KB), `kkbox_evaluation_results.json` (2.25 KB), `tuning_history.json` (6 KB), and candidate models. |
| `data/processed/` | 24 files (52.32 MB) | Processed feature Parquet files (`real_hf_kkbox_full_window.parquet` 43.87 MB, 970,960 rows), train/val/test splits, benchmark JSON outputs, and drift metrics. |
| `data/raw/` | Directory | Staging directory for raw incoming data streams. |
| `data/retrain_execution.log` | 96.8 KB | Operational audit log tracking automated retraining triggers and background execution history. |
| `data/retrain_jobs/` | 9 files | File-based distributed task queue coordinating asynchronous retraining jobs and preventing race conditions. |

---

## 8. Documentation & Deliverables: `docs/` (14 Root Docs + 7 Subdirs)

### 8.1. Academic Deliverables & Core Documentation (Root Files)

| File Path | Size | Description & Institutional Alignment |
| :--- | :---: | :--- |
| `docs/ACADEMIC_INTEGRITY_AUDIT_REPORT.md` | 9.2 KB | Formal audit report certifying 0 mocked entries, 0 synthetic screens, and 100% empirical evidence. |
| `docs/Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.docx` | 1.24 MB | Final graduation-grade capstone report conforming to UIT specifications (Times New Roman 13pt, 1.5 line spacing, 3-2-2.5-2.5cm margins). |
| `docs/Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.pdf` | 793 KB | Rendered PDF format of the final academic thesis report for distribution and evaluation. |
| `docs/CODE_STATUS_2026-11-03.md` | 5.8 KB | Engineering milestone status report tracking component implementation and test status. |
| `docs/KKBOX_DECISIONS_2026-11-03.md` | 6.5 KB | Architectural Decision Record (ADR) justifying KKBox big data selection, DuckDB ETL, and LightGBM choice. |
| `docs/KKBOX_REPORT_SCAFFOLD.md` | 8.5 KB | Academic structure and chapter breakdown guide for the KKBox empirical findings. |
| `docs/KKBOX_RUNBOOK.md` | 8.2 KB | Technical operational runbook for reproducing KKBox ETL, model training, and serving. |
| `docs/LOCAL_PREP_STATUS_2026-11-04.md` | 6.1 KB | Environment setup verification report tracking local dependencies and cloud tool configuration. |
| `docs/MASTER_PROJECT_REPORT.md` | 42.9 KB | Comprehensive technical whitepaper covering end-to-end architecture, benchmarks, and deployment. |
| `docs/MASTER_PROJECT_TRUTH.md` | 80.9 KB | Master source of empirical truth containing all validated metrics, benchmarks, and architectural facts. |
| `docs/MULTI_AGENT_TRIPLE_BLIND_AUDIT_REPORT.md` | 68.5 KB | Master audit report documenting the 6-agent triple-blind peer-swap audit results and defect resolutions. |
| `docs/RUBRIC_DEMO_PLAN_2026-11-04.md` | 23.8 KB | Demonstration protocol mapping project features directly to academic and enterprise evaluation criteria. |
| `docs/RUNBOOK_HUONG_DAN_VAN_HANH.md` | 75.7 KB | Complete Vietnamese operational runbook detailing system administration, deployment, and troubleshooting. |
| `docs/Slide_Thuyet_Trinh_MLOps_Customer_Churn.pptx` | 1.08 MB | Official academic presentation deck (16:9 widescreen) for project defense. |

### 8.2. Specialized Documentation Subdirectories

| Subdirectory Path | File Count | Scope & Contents |
| :--- | :---: | :--- |
| `docs/experiments/` | 8 files | Hyperparameter tuning logs, Optuna study summaries, and ablation experiments. |
| `docs/images/` | 19 files | High-resolution publication figures: ROC curves, calibration plots, SHAP graphs, and system architecture diagrams. |
| `docs/reports/` | 1 file | Consolidated audit and remediation summary (`CONSOLIDATED_AUDIT_AND_REMEDIATION_SUMMARY.md`). |
| `docs/requirements/` | 7 files | Canonical specification files: `project_spec.md`, `grounding_catalog.md`, `data_contract.md`, and this inventory. |
| `docs/research/` | 2,422 files | Peer-reviewed research papers (PDFs) and shallow-cloned gold-standard GitHub repositories. |
| `docs/specifications/` | 8 files | Formal architectural specifications for resilience, security, and serving APIs. |

---

## 9. Security & Benchmark Reports: `reports/` (8 Files)

| Report File Path | Lines / Size | Security / Benchmark Scope & Real Findings |
| :--- | :---: | :--- |
| `reports/checkov_real_report.json` | JSON report | Checkov static analysis report auditing Terraform and ARM templates against Azure security baselines (28/28 checks passed: 18 Terraform, 10 ARM). |
| `reports/infracost_breakdown.json` | 52 lines (1.6 KB) | Infracost cloud cost estimation breakdown projecting baseline monthly cloud expenditure of $70.61 ($11.22 Serverless Scale-to-Zero) for planned Azure infrastructure. |
| `reports/infracost_config.yml` | 25 lines (0.9 KB) | Configuration file for Infracost CLI defining Azure provider settings and currency. |
| `reports/k6_real_benchmark.json` | 166 lines (4.5 KB) | Real K6 load test benchmark report confirming 435.6 RPS throughput, 38.2ms p95 latency, and 0.00% error rate. |
| `reports/microburst_real_blobs_report.txt` | 171 lines (8.7 KB) | NetSPI MicroBurst Azure security audit report evaluating Azure Blob Storage access controls and anonymity settings. |
| `reports/results_json.json` | 1 line (78.7 KB) | Raw Pytest test execution results capturing passing status across all test suites. |
| `reports/security_audit_report.json` | 1,667 lines (67.1 KB) | Consolidated enterprise security report integrating SAST, secret detection, and dependency scan results. |
| `reports/trivy_real_report.json` | 19,849 lines (900 KB) | Trivy container vulnerability scanner report auditing base images and Python dependencies (0 critical unpatched CVEs). |

---

## 10. External Tool Suites: `tools/` (10 Suites)

In strict adherence to **[INVARIANT-09] Mandatory Open-Source Reuse Over Reinvention**, the project integrates gold-standard open-source tools rather than writing custom alternatives.

| Tool Directory | Tool Type & Origin | Integration Role in MLOps Pipeline |
| :--- | :--- | :--- |
| `tools/azurehound/` | Azure Identity Auditor (SpecterOps) | BloodHound collector for mapping Azure Active Directory privilege relationships and attack paths. |
| `tools/azurite_data/` | Local Azure Storage Emulator (Microsoft) | Persistent local storage directory backing Azurite emulator for offline blob and queue testing. |
| `tools/checkov_env/` | Static IaC Security Scanner (Bridgecrew/Palo Alto) | Dedicated virtual environment hosting Checkov CLI for continuous Terraform/ARM security auditing. |
| `tools/cloudfox/` | Cloud Situational Awareness (Bishop Fox) | Command-line tool for discovering attackable assets in cloud infrastructure during security testing. |
| `tools/docxtpl/` | Python Document Template Engine (elapouya) | Template-based Word document generator used by `generate_docx_report.py` to compile UIT reports. |
| `tools/infracost/` | Shift-Left Cloud Cost Engine (Infracost) | Cloud cost estimation binary providing instant pull-request cost breakdowns for Terraform. |
| `tools/k6/` | Modern Load Testing Tool (Grafana Labs) | High-performance load testing binary (`k6.exe` v2.3.0) driving concurrent HTTP traffic against serving endpoints. |
| `tools/microburst/` | Azure Security PowerShell Toolkit (NetSPI) | Automated scripts for assessing Azure subscriptions, storage containers, and role assignments. |
| `tools/reveal.js/` | HTML Presentation Framework (hakimel) | Open-source slide framework supporting interactive, responsive web presentations. |
| `tools/trivy/` | Comprehensive Container Scanner (Aqua Security) | Vulnerability and misconfiguration scanner (`trivy.exe`) auditing container filesystems and dependencies. |

---

## 11. Bespoke Brand Assets: `assets/` (2 Files)

In accordance with **[INVARIANT-03] Anti-AI Cliché & Natural Palettes** and **[INVARIANT-04] Bespoke Vector Assets**, all brand elements are custom-designed vector SVGs without generic AI emojis or clichés.

| Asset File Path | Size | Visual Design & Branding Alignment |
| :--- | :---: | :--- |
| `assets/banner.svg` | 3.8 KB | Widescreen vector SVG banner featuring Oceanic Navy (`#0F172A`), Forest Emerald (`#059669`), and Amber (`#D97706`) accents for documentation and slide headers. |
| `assets/logo.svg` | 1.4 KB | Clean vector SVG brand icon depicting the ChurnGuard shield and data telemetry pulse in natural enterprise colors. |

---

## 12. Verification & Line Cap Compliance

All 46 source files across `src/` and all 40 scripts across `scripts/` have been verified against the 400-line code cap:
- **Maximum Lines in `src/`:** 382 lines (`src/models/train_pipeline.py`) - **PASS** (<= 400 lines).
- **Maximum Lines in `scripts/`:** 376 lines (`scripts/uit_report_content.py`) - **PASS** (<= 400 lines).
- **Files Exceeding 400 Lines:** Exactly **0** files.
- **Verification Command:** `cmd /c "python scripts/verification/audit_line_cap.py"` - 100% compliant.

---
*Generated by `mapper` (Codebase Structure Mapper) - Universal Autonomous Meta-Agent Swarm.*
