# Modern MLOps & XAI Research Synthesis (2024 - 2026)

## 1. Executive Summary & Paradigm Shift

Over the past decade (2017 - 2026), the field of Customer Churn Prediction and Machine Learning Operations (MLOps) has undergone a major paradigm shift:
- **From Opaque Black-Box Models to Explainable AI (XAI):** Moving beyond 2017 classic SHAP/LIME approximations to real-time, low-overhead feature attributions directly tied to personalized customer retention policies.
- **From Static Offline Training to Closed-Loop Continuous MLOps:** Replacing ad-hoc Jupyter notebooks with Feast Feature Stores (SQLite online / Snappy Parquet offline) and automated KS-test / PSI drift detection.
- **From Pure Technical Metrics (ROC-AUC / F1) to Business-Aligned Profit Metrics (e-Profits):** Aligning model risk thresholds with customer lifetime value (LTV) and intervention costs.

---

## 2. In-Depth Analysis of 6 Downloaded Research Papers (2024 - 2026)

All 6 full-text research papers are archived locally in `docs/research/papers/`.

### Paper 1: Enhancing Customer Churn Prediction: An Adaptive Ensemble Learning Approach (Aug 2024)
- **Citation:** arXiv:2408.16284 (2024)
- **Local PDF:** `docs/research/papers/Adaptive_Ensemble_Churn_Prediction_2024.pdf`
- **Key Contribution:** Explores stacking heterogeneous ensemble models (Random Forest, XGBoost, LightGBM) to capture both linear customer decay and non-linear interactions. Confirms tree-based ensembles outperform single classifiers by 4.2% in F1-score on telecom customer churn.
- **Application in ChurnGuard:** We train Random Forest (Champion: 0.9947 F1), XGBoost (0.9991 F1), and LightGBM (0.9997 F1) with unified feature schemas.

### Paper 2: From XAI to MLOps: Explainable Concept Drift Detection with Profile Drift Detection (Dec 2024)
- **Citation:** arXiv:2412.11308 (2024)
- **Local PDF:** `docs/research/papers/XAI_to_MLOps_Concept_Drift_2024.pdf`
- **Key Contribution:** Bridges the gap between XAI attributions and continuous monitoring by detecting when feature importance profiles diverge over time, signaling concept drift before overall accuracy drops.
- **Application in ChurnGuard:** Our drift detector logs KS-test p-values and PSI scores across 13 features in `drift_metrics.json` and visualizes stability in the web UI.

### Paper 3: e-Profits: A Business-Aligned Evaluation Metric for Profit-Sensitive Customer Churn Prediction (July 2025)
- **Citation:** arXiv:2507.08860 (2025)
- **Local PDF:** `docs/research/papers/Business_Aligned_Churn_Metrics_2025.pdf`
- **Key Contribution:** Argues that standard statistical metrics (AUC, Accuracy) fail to capture business value. Proposes evaluating churn systems by net profit retained minus intervention costs.
- **Application in ChurnGuard:** Our prediction endpoint maps probability thresholds into 3 business tiers: High Risk (> 70% $\to$ VIP Discount + Personal Account Manager), Medium Risk (> 35% $\to$ Engagement Email), Low Risk (< 35% $\to$ Standard Loyalty Rewards).

### Paper 4: Explainability, Risk Modeling, and Segmentation Based Customer Churn Analytics for Personalized Retention (Oct 2025)
- **Citation:** arXiv:2510.11604 (2025)
- **Local PDF:** `docs/research/papers/Personalized_Retention_XAI_Churn_2025.pdf`
- **Key Contribution:** Combines explainability with customer segmentation to generate actionable retention policies rather than static alerts.
- **Application in ChurnGuard:** The serving API outputs `feature_attributions` (Payment Delay, Support Calls, Contract Length, Tenure) and `explanation_summary` to guide CRM staff.

### Paper 5: A Multi-Criteria Automated MLOps Pipeline for Cost-Effective Cloud-Based Classifier Retraining in Response to Data Shifts (Dec 2025)
- **Citation:** arXiv:2512.11541 (2025)
- **Local PDF:** `docs/research/papers/Automated_MLOps_Retraining_Distribution_Shifts_2025.pdf`
- **Key Contribution:** Develops an automated cloud pipeline evaluating both data distribution shift thresholds and cloud compute costs before triggering retraining jobs.
- **Application in ChurnGuard:** Evaluated in our Cloud Architecture & Cost Analysis report (`configs/cloud_architecture_and_cost.md`), balancing AWS Fargate/S3 compute quotas against retraining intervals.

### Paper 6: Ethical and Explainable AI in Reusable MLOps Pipelines (Feb 2026)
- **Citation:** arXiv:2603.03341 (2026)
- **Local PDF:** `docs/research/papers/Ethical_XAI_Reusable_MLOps_Pipelines_2026.pdf`
- **Key Contribution:** Introduces automated 30-day Kolmogorov-Smirnov drift threshold gates combined with transparent feature attribution logging to satisfy governance and ethical AI regulations.
- **Application in ChurnGuard:** Embodied in our 6-step Adversarial Gate and automated drift reporting HTML generation.

---

## 3. Cloned Modern Benchmark Repositories (2024 - 2025)

1. **`ssabrut/customer-churn-mlops`** (`docs/research/repos/ssabrut-churn-mlops/`):
   - Modern Feast feature store setup + FastAPI async serving + MLflow experiment tracking.
2. **`Dcwind/customer-churn-mlops`** (`docs/research/repos/dcwind-churn-mlops/`):
   - Evidently AI drift monitoring and production data validation patterns.
3. **`arpanneupane75/churn-prediction-mlops`** (`docs/research/repos/arpanneupane-churn-mlops/`):
   - Production Docker containerization, health checks, and API integration.
