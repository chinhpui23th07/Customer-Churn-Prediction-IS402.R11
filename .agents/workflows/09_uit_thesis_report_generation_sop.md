---
id: workflow-09-uit-thesis-report-generation-sop
title: Standard Operating Procedure (SOP) for UIT Graduation Thesis & Capstone Report Generation
---

# SOP 09: UIT Thesis & Capstone Report Generation Procedure

## 1. Purpose
Defines the standardized pipeline for synthesizing experimental results, benchmarks, and IEEE references into an official Microsoft Word (`.docx`) report conforming to University of Information Technology (UIT - VNU-HCM) graduation standards.

---

## 2. Step-by-Step SOP

```text
[Step 1: Collect Empirical Telemetry]
  ├── data/processed/io_benchmark_results.json (I/O throughput & file compression)
  ├── data/processed/region_latency_results.json (Multi-region TCP RTT)
  ├── data/processed/drift_metrics.json (KS-test & PSI scores)
  └── data/processed/evaluation_results.json (Model classification metrics)
       │
       ▼
[Step 2: Prepare High-Resolution Figures (300 DPI)]
  ├── docs/images/model_metrics_comparison.png
  ├── docs/images/roc_curves.png
  ├── docs/images/confusion_matrices.png
  └── docs/images/feature_importance.png
       │
       ▼
[Step 3: Render Complete UIT Document Hierarchy]
  ├── Official Cover & Inner Sub-Cover with decorative borders
  ├── Pledge of Authorship & Acknowledgments
  ├── Bilingual Abstract (Vietnamese & English)
  ├── Table of Contents, Lists of Tables, Figures, Abbreviations
  └── 6 Core UIT Chapters with IEEE bibliography
       │
       ▼
[Step 4: Execute Document Synthesis]
  └── cmd /c "python scripts\generate_docx_report.py"
```
