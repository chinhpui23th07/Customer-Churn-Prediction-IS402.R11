# 🎯 GAP ANALYSIS: TẠI SAO CHƯA ĐẠT 10 ĐIỂM?

> **Điểm hiện tại:** 8.5/10.0 (A-)  
> **Mục tiêu:** 10.0/10.0 (A+)  
> **Gap:** -1.5 điểm cần cải thiện  

---

## 📊 PHÂN TÍCH CHI TIẾT ĐIỂM THIẾU

### 🔴 THIẾU 1: Hyperparameter Tuning (-0.4 điểm)

**Hiện tại:**
```python
# train_pipeline.py:
clf = XGBClassifier(
    n_estimators=100,      # ← Hard-coded!
    max_depth=12,          # ← Hard-coded!
    learning_rate=0.1,     # ← Hard-coded!
    random_state=42
)
```

**Vấn đề:**
- ❌ Không có GridSearchCV hoặc RandomizedSearchCV
- ❌ Không có Optuna hoặc hyperopt
- ❌ Không justify tại sao chọn n_estimators=100, max_depth=12
- ❌ Không có tuning history
- ❌ Không có best_params_ documentation

**Yêu cầu để đạt điểm tối đa:**
```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
import optuna  # hoặc hyperopt

# Option 1: GridSearchCV (exhaustive)
param_grid = {
    'n_estimators': [50, 100, 150, 200],
    'max_depth': [6, 8, 10, 12, 15],
    'learning_rate': [0.01, 0.05, 0.1, 0.3],
    'subsample': [0.7, 0.8, 0.9, 1.0],
    'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
    'min_child_weight': [1, 3, 5, 7],
    'gamma': [0, 0.1, 0.2, 0.3]
}

grid_search = GridSearchCV(
    estimator=XGBClassifier(random_state=42),
    param_grid=param_grid,
    cv=5,
    scoring='roc_auc',
    n_jobs=-1,
    verbose=1
)

grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_
best_params = grid_search.best_params_

print(f"Best params: {best_params}")
print(f"Best CV score: {grid_search.best_score_}")

# Save tuning history
tuning_history = {
    "method": "GridSearchCV",
    "param_grid": param_grid,
    "best_params": best_params,
    "best_cv_score": grid_search.best_score_,
    "cv_results": grid_search.cv_results_
}

with open("data/models/tuning_history.json", "w") as f:
    json.dump(tuning_history, f, indent=2)

# Option 2: Optuna (Bayesian optimization - BETTER!)
import optuna

def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 0, 0.5),
        'reg_alpha': trial.suggest_float('reg_alpha', 0, 1.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0, 1.0),
        'random_state': 42
    }
    
    clf = XGBClassifier(**params)
    scores = cross_val_score(clf, X_train, y_train, cv=5, scoring='roc_auc')
    return scores.mean()

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100, timeout=3600)

print(f"Best trial: {study.best_trial.params}")
print(f"Best CV ROC-AUC: {study.best_value}")

# Save study
joblib.dump(study, "data/models/optuna_study.pkl")
```

**Lý do trừ điểm:**
- Rubric MLOps yêu cầu "systematic hyperparameter optimization"
- Hard-coded params không có scientific justification
- Competitive ML projects ALWAYS tune hyperparameters

**Impact:** -0.4 điểm

---

### 🔴 THIẾU 2: Learning Curves & Model Analysis (-0.3 điểm)

**Hiện tại:**
- ❌ Không có learning curves (training size vs performance)
- ❌ Không có feature importance analysis chi tiết
- ❌ Không có error analysis (FP, FN breakdown)
- ❌ Không có calibration curve
- ❌ Không có confusion matrix heatmap visualization

**Yêu cầu để đạt điểm tối đa:**

```python
import matplotlib.pyplot as plt
from sklearn.model_selection import learning_curve
from sklearn.metrics import plot_confusion_matrix, plot_roc_curve
from sklearn.calibration import calibration_curve

# 1. Learning Curves
train_sizes, train_scores, val_scores = learning_curve(
    clf, X_train, y_train, 
    cv=5, 
    train_sizes=np.linspace(0.1, 1.0, 10),
    scoring='roc_auc',
    n_jobs=-1
)

plt.figure(figsize=(10, 6))
plt.plot(train_sizes, train_scores.mean(axis=1), label='Training score')
plt.plot(train_sizes, val_scores.mean(axis=1), label='Validation score')
plt.xlabel('Training Size')
plt.ylabel('ROC-AUC Score')
plt.title('Learning Curves')
plt.legend()
plt.grid()
plt.savefig('docs/learning_curves.png')

# 2. Feature Importance Analysis
feature_importance = pd.DataFrame({
    'feature': FEATURE_COLS,
    'importance': clf.feature_importances_
}).sort_values('importance', ascending=False)

plt.figure(figsize=(10, 8))
plt.barh(feature_importance['feature'], feature_importance['importance'])
plt.xlabel('Importance')
plt.title('Feature Importance (XGBoost)')
plt.tight_layout()
plt.savefig('docs/feature_importance.png')

# 3. Calibration Curve
prob_true, prob_pred = calibration_curve(
    y_test, clf.predict_proba(X_test)[:, 1], n_bins=10
)

plt.figure(figsize=(8, 8))
plt.plot([0, 1], [0, 1], 'k--', label='Perfect calibration')
plt.plot(prob_pred, prob_true, marker='o', label='XGBoost')
plt.xlabel('Predicted Probability')
plt.ylabel('True Probability')
plt.title('Calibration Curve')
plt.legend()
plt.grid()
plt.savefig('docs/calibration_curve.png')

# 4. Error Analysis
y_pred = clf.predict(X_test)
y_proba = clf.predict_proba(X_test)[:, 1]

# False Positives analysis
fp_mask = (y_test == 0) & (y_pred == 1)
fp_data = X_test[fp_mask]
fp_proba = y_proba[fp_mask]

print(f"False Positives: {fp_mask.sum()}")
print(f"FP probability distribution:")
print(pd.Series(fp_proba).describe())

# False Negatives analysis
fn_mask = (y_test == 1) & (y_pred == 0)
fn_data = X_test[fn_mask]
fn_proba = y_proba[fn_mask]

print(f"False Negatives: {fn_mask.sum()}")
print(f"FN probability distribution:")
print(pd.Series(fn_proba).describe())

# 5. Confusion Matrix Visualization
from sklearn.metrics import ConfusionMatrixDisplay

fig, ax = plt.subplots(figsize=(8, 6))
ConfusionMatrixDisplay.from_estimator(
    clf, X_test, y_test, ax=ax, cmap='Blues'
)
plt.title('Confusion Matrix')
plt.savefig('docs/confusion_matrix.png')
```

**Lý do trừ điểm:**
- Top-tier ML projects always include model diagnostics
- Learning curves show if model is under/overfitting
- Error analysis reveals model weaknesses
- Required for production deployment decisions

**Impact:** -0.3 điểm

---

### 🔴 THIẾU 3: Advanced Data Quality Checks (-0.2 điểm)

**Hiện tại:**
- ✅ Có duplicate detection
- ✅ Có customer ID isolation check
- ❌ Không có outlier detection & handling
- ❌ Không có data drift baseline validation
- ❌ Không có Great Expectations integration
- ❌ Không có schema validation

**Yêu cầu để đạt điểm tối đa:**

```python
# 1. Outlier Detection
from scipy import stats

def detect_outliers(df, columns, method='iqr', threshold=3):
    """
    Detect outliers using IQR or Z-score method
    """
    outliers = pd.DataFrame()
    
    for col in columns:
        if method == 'iqr':
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            mask = (df[col] < lower) | (df[col] > upper)
        elif method == 'zscore':
            z_scores = np.abs(stats.zscore(df[col]))
            mask = z_scores > threshold
        
        outliers[col] = mask
    
    return outliers

# Run outlier detection
numeric_cols = ['age', 'tenure', 'total_spend', 'payment_delay', 
                'support_calls', 'usage_frequency', 'last_interaction']

outlier_report = detect_outliers(df, numeric_cols, method='iqr', threshold=3)

print("\n=== OUTLIER REPORT ===")
for col in numeric_cols:
    n_outliers = outlier_report[col].sum()
    pct = n_outliers / len(df) * 100
    print(f"{col}: {n_outliers} outliers ({pct:.2f}%)")

# 2. Great Expectations Integration
import great_expectations as ge

ge_df = ge.from_pandas(df)

# Define expectations
ge_df.expect_column_values_to_be_between('age', min_value=18, max_value=100)
ge_df.expect_column_values_to_be_between('tenure', min_value=0, max_value=120)
ge_df.expect_column_values_to_not_be_null('customerid')
ge_df.expect_column_values_to_be_unique('customerid')
ge_df.expect_column_values_to_be_in_set('gender', ['Male', 'Female'])
ge_df.expect_column_values_to_be_in_set(
    'subscription_type', ['Basic', 'Standard', 'Premium']
)

# Run validation
results = ge_df.validate()

# Save expectation suite
ge_df.save_expectation_suite('expectations/churn_data_suite.json')

# 3. Schema Validation
from pydantic import BaseModel, validator, Field
from typing import Literal

class ChurnDataSchema(BaseModel):
    customerid: int = Field(..., ge=1)
    age: float = Field(..., ge=18, le=100)
    gender: Literal['Male', 'Female']
    tenure: float = Field(..., ge=0, le=120)
    usage_frequency: float = Field(..., ge=0, le=100)
    support_calls: float = Field(..., ge=0, le=50)
    payment_delay: float = Field(..., ge=0, le=365)
    subscription_type: Literal['Basic', 'Standard', 'Premium']
    contract_length: Literal['Monthly', 'Quarterly', 'Annual']
    total_spend: float = Field(..., ge=0)
    last_interaction: float = Field(..., ge=0, le=365)
    churn: Literal[0, 1]
    
    @validator('total_spend')
    def validate_spend(cls, v, values):
        if 'tenure' in values and values['tenure'] > 0:
            spend_per_month = v / values['tenure']
            if spend_per_month > 10000:  # Suspiciously high
                raise ValueError('Spend per month too high')
        return v

# Validate all rows
for idx, row in df.iterrows():
    try:
        ChurnDataSchema(**row.to_dict())
    except Exception as e:
        print(f"Row {idx} validation error: {e}")

# 4. Data Quality Report
quality_report = {
    "total_rows": len(df),
    "duplicates": df.duplicated().sum(),
    "missing_values": df.isnull().sum().to_dict(),
    "outliers": {col: outlier_report[col].sum() for col in numeric_cols},
    "data_types": df.dtypes.astype(str).to_dict(),
    "unique_customers": df['customerid'].nunique(),
    "date_range": {
        "min": df['event_timestamp'].min().isoformat() if 'event_timestamp' in df else None,
        "max": df['event_timestamp'].max().isoformat() if 'event_timestamp' in df else None
    }
}

with open('data/processed/data_quality_report.json', 'w') as f:
    json.dump(quality_report, f, indent=2)
```

**Lý do trừ điểm:**
- Production ML systems need comprehensive data validation
- Great Expectations is industry standard
- Schema validation prevents silent data corruption
- Outlier handling affects model performance

**Impact:** -0.2 điểm

---

### 🔴 THIẾU 4: Model Monitoring Dashboard & Alerts (-0.2 điểm)

**Hiện tại:**
- ✅ Có drift detection
- ✅ Có PSI calculation
- ❌ Không có dashboard visualization
- ❌ Không có alerting system
- ❌ Không có Prometheus/Grafana integration
- ❌ Không có SLA monitoring

**Yêu cầu để đạt điểm tối đa:**

```python
# 1. Prometheus Metrics Export
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
prediction_counter = Counter(
    'churn_predictions_total', 
    'Total number of predictions',
    ['model_version', 'result']
)

prediction_latency = Histogram(
    'churn_prediction_latency_seconds',
    'Prediction latency in seconds'
)

drift_gauge = Gauge(
    'churn_drift_score',
    'Current data drift score',
    ['feature']
)

# Update metrics in API
@app.post("/predict")
def predict_single(customer: CustomerInput):
    start_time = time.time()
    
    # ... prediction logic ...
    
    # Update metrics
    prediction_counter.labels(
        model_version=MODEL_ARTIFACT['version'],
        result='churn' if pred_class == 1 else 'no_churn'
    ).inc()
    
    prediction_latency.observe(time.time() - start_time)
    
    return result

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

# 2. Real-time Dashboard (Streamlit)
# dashboard.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="ChurnGuard MLOps Dashboard", layout="wide")

st.title("🎯 ChurnGuard MLOps Monitoring Dashboard")

# KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Predictions", "15,432", "+234")
    
with col2:
    st.metric("Churn Rate", "56.8%", "-2.3%")
    
with col3:
    st.metric("Avg Latency", "2.3ms", "+0.1ms")
    
with col4:
    drift_status = "✅ Stable" if drift_share < 0.33 else "🚨 DRIFT"
    st.metric("Data Drift", drift_status)

# Drift monitoring chart
if os.path.exists('data/processed/drift_metrics.json'):
    with open('data/processed/drift_metrics.json') as f:
        drift_data = json.load(f)
    
    features = list(drift_data['features'].keys())
    psi_scores = [drift_data['features'][f]['psi_score'] for f in features]
    
    fig = go.Figure(data=[
        go.Bar(x=features, y=psi_scores, marker_color='lightblue')
    ])
    fig.add_hline(y=0.25, line_dash="dash", line_color="red", 
                  annotation_text="PSI Threshold (0.25)")
    fig.update_layout(title="Feature Drift Monitoring (PSI Scores)")
    st.plotly_chart(fig, use_container_width=True)

# Model performance over time
st.subheader("📊 Model Performance Over Time")

# Load historical metrics
history_df = pd.read_csv('data/models/performance_history.csv')

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=history_df['timestamp'], 
    y=history_df['roc_auc'],
    name='ROC-AUC',
    line=dict(color='blue')
))
fig.add_trace(go.Scatter(
    x=history_df['timestamp'], 
    y=history_df['f1_score'],
    name='F1 Score',
    line=dict(color='green')
))
fig.update_layout(title="Model Performance Tracking")
st.plotly_chart(fig, use_container_width=True)

# 3. Alerting System
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, message, alert_level='WARNING'):
    """
    Send email alert when drift or performance degradation detected
    """
    recipients = ['mlops-team@company.com']
    
    msg = MIMEText(message)
    msg['Subject'] = f"[{alert_level}] ChurnGuard MLOps: {subject}"
    msg['From'] = 'mlops-alerts@company.com'
    msg['To'] = ', '.join(recipients)
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('mlops-alerts@company.com', os.getenv('EMAIL_PASSWORD'))
        server.send_message(msg)

# Check for drift and send alert
def check_and_alert():
    drift_result = run_drift_analysis()
    
    if drift_result['dataset_drift_detected']:
        send_alert(
            subject="Data Drift Detected",
            message=f"""
            Data drift detected in production!
            
            Drifted features: {drift_result['drifted_features_count']}/{drift_result['total_features']}
            Drift share: {drift_result['drift_share']*100:.1f}%
            
            Action required: Review model performance and consider retraining.
            
            Dashboard: http://mlops-dashboard.company.com
            """,
            alert_level='WARNING'
        )

# 4. SLA Monitoring
class SLAMonitor:
    def __init__(self):
        self.sla_targets = {
            'latency_p95_ms': 50,  # 95th percentile < 50ms
            'latency_p99_ms': 100,  # 99th percentile < 100ms
            'uptime_pct': 99.9,     # 99.9% uptime
            'error_rate_pct': 0.1   # < 0.1% errors
        }
        self.metrics_history = []
    
    def check_sla_compliance(self, current_metrics):
        violations = []
        
        for metric, target in self.sla_targets.items():
            if current_metrics[metric] > target:
                violations.append({
                    'metric': metric,
                    'target': target,
                    'actual': current_metrics[metric]
                })
        
        if violations:
            send_alert(
                subject="SLA Violation Detected",
                message=f"SLA violations: {violations}",
                alert_level='CRITICAL'
            )
        
        return len(violations) == 0

sla_monitor = SLAMonitor()
```

**Lý do trừ điểm:**
- Production MLOps requires monitoring & alerting
- Dashboards enable proactive issue detection
- SLA compliance is critical for business
- Industry standard for mature ML systems

**Impact:** -0.2 điểm

---

### 🔴 THIẾU 5: A/B Testing & Champion/Challenger Pattern (-0.2 điểm)

**Hiện tại:**
- ✅ Có champion model selection
- ❌ Không có A/B testing framework
- ❌ Không có champion/challenger deployment
- ❌ Không có traffic splitting
- ❌ Không có statistical significance testing

**Yêu cầu để đạt điểm tối đa:**

```python
# 1. Champion/Challenger Routing
import random
from enum import Enum

class ModelVersion(Enum):
    CHAMPION = "v1.0.0-champion"
    CHALLENGER = "v2.0.0-challenger"

# Load both models
champion_model = joblib.load('data/models/champion_model.joblib')
challenger_model = joblib.load('data/models/challenger_model.joblib')

# A/B test configuration
AB_TEST_CONFIG = {
    "enabled": True,
    "traffic_split": {
        ModelVersion.CHAMPION: 0.9,    # 90% traffic
        ModelVersion.CHALLENGER: 0.1   # 10% traffic
    }
}

def select_model_for_request(customer_id: int):
    """
    Route request to champion or challenger based on A/B test config
    """
    if not AB_TEST_CONFIG["enabled"]:
        return champion_model, ModelVersion.CHAMPION
    
    # Deterministic routing based on customer_id
    hash_val = hash(customer_id) % 100
    threshold = AB_TEST_CONFIG["traffic_split"][ModelVersion.CHAMPION] * 100
    
    if hash_val < threshold:
        return champion_model, ModelVersion.CHAMPION
    else:
        return challenger_model, ModelVersion.CHALLENGER

@app.post("/predict")
def predict_single(customer: CustomerInput):
    # Select model via A/B test
    model, version = select_model_for_request(customer.customer_id)
    
    # ... prediction logic with selected model ...
    
    # Log which model was used
    log_inference_prediction(
        customer_id=customer.customer_id,
        features=features,
        pred=pred_class,
        prob=prob,
        model_version=version.value
    )
    
    return result

# 2. A/B Test Analysis
def analyze_ab_test():
    """
    Compare champion vs challenger performance with statistical tests
    """
    import scipy.stats as stats
    
    # Load predictions from both models
    conn = sqlite3.connect(INFERENCE_DB)
    
    champion_df = pd.read_sql("""
        SELECT * FROM inference_logs 
        WHERE model_version = ?
    """, conn, params=[ModelVersion.CHAMPION.value])
    
    challenger_df = pd.read_sql("""
        SELECT * FROM inference_logs 
        WHERE model_version = ?
    """, conn, params=[ModelVersion.CHALLENGER.value])
    
    conn.close()
    
    # Compare average latency
    t_stat, p_value = stats.ttest_ind(
        champion_df['latency_ms'], 
        challenger_df['latency_ms']
    )
    
    print(f"Latency comparison:")
    print(f"  Champion: {champion_df['latency_ms'].mean():.2f}ms")
    print(f"  Challenger: {challenger_df['latency_ms'].mean():.2f}ms")
    print(f"  T-statistic: {t_stat:.4f}, p-value: {p_value:.4f}")
    
    # Compare churn rate predictions
    churn_rate_champ = champion_df['churn_prediction'].mean()
    churn_rate_chall = challenger_df['churn_prediction'].mean()
    
    # Chi-square test
    chi2, p_val = stats.chi2_contingency([
        [champion_df['churn_prediction'].sum(), len(champion_df) - champion_df['churn_prediction'].sum()],
        [challenger_df['churn_prediction'].sum(), len(challenger_df) - challenger_df['churn_prediction'].sum()]
    ])[:2]
    
    print(f"\nChurn rate comparison:")
    print(f"  Champion: {churn_rate_champ:.4f}")
    print(f"  Challenger: {churn_rate_chall:.4f}")
    print(f"  Chi-square: {chi2:.4f}, p-value: {p_val:.4f}")
    
    # Decision rule
    if p_val < 0.05 and churn_rate_chall < churn_rate_champ:
        print("\n✅ Challenger is significantly better! Promote to champion.")
        return "promote"
    else:
        print("\n⏸️ No significant improvement. Keep champion.")
        return "keep_champion"

# 3. Gradual Rollout
def gradual_rollout(initial_pct=0.05, increment=0.05, max_pct=1.0, hours_between=24):
    """
    Gradually increase challenger traffic from 5% to 100%
    """
    current_pct = initial_pct
    
    while current_pct <= max_pct:
        # Update traffic split
        AB_TEST_CONFIG["traffic_split"][ModelVersion.CHALLENGER] = current_pct
        AB_TEST_CONFIG["traffic_split"][ModelVersion.CHAMPION] = 1.0 - current_pct
        
        print(f"🚀 Rollout: {current_pct*100:.0f}% traffic to challenger")
        
        # Wait and monitor
        time.sleep(hours_between * 3600)
        
        # Check for issues
        recent_errors = check_error_rate(hours=hours_between)
        if recent_errors > 0.01:  # > 1% error rate
            print("🚨 High error rate detected! Rolling back...")
            AB_TEST_CONFIG["traffic_split"][ModelVersion.CHALLENGER] = 0.0
            AB_TEST_CONFIG["traffic_split"][ModelVersion.CHAMPION] = 1.0
            send_alert("Rollout Failed", f"Error rate: {recent_errors*100:.2f}%")
            break
        
        current_pct += increment
    
    print("✅ Rollout complete!")
```

**Lý do trừ điểm:**
- A/B testing is essential for safe model deployment
- Champion/Challenger pattern is ML production best practice
- Statistical significance testing prevents bad deployments
- Required by Google/Facebook/Netflix ML systems

**Impact:** -0.2 điểm

---

### 🔴 THIẾU 6: CI/CD Pipeline & Automation (-0.2 điểm)

**Hiện tại:**
- ❌ Không có GitHub Actions workflow
- ❌ Không có automated testing
- ❌ Không có automated deployment
- ❌ Không có model registry integration
- ❌ Không có containerization (Docker)

**Yêu cầu để đạt điểm tối đa:**

```yaml
# .github/workflows/mlops-pipeline.yml
name: MLOps CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 0'  # Weekly retrain

jobs:
  data-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run data quality checks
        run: |
          python src/data/validate_data.py
          python src/data/check_drift.py
      
      - name: Great Expectations validation
        run: |
          great_expectations checkpoint run churn_data_checkpoint

  model-training:
    needs: data-validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Download data
        run: |
          dvc pull data/raw.dvc
      
      - name: Run preprocessing
        run: |
          python src/data/preprocess.py
      
      - name: Train models
        run: |
          python src/models/train_pipeline.py
      
      - name: Evaluate models
        run: |
          python src/models/evaluate.py
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v2
        with:
          name: trained-models
          path: data/models/

  model-testing:
    needs: model-training
    runs-on: ubuntu-latest
    steps:
      - name: Run unit tests
        run: |
          pytest tests/test_preprocessing.py -v
          pytest tests/test_models.py -v
          pytest tests/test_api.py -v
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v
      
      - name: Check model performance
        run: |
          python tests/test_model_performance.py
          # Fail if ROC-AUC < 0.85 (excluding bias)
      
      - name: Test API endpoints
        run: |
          python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
          pytest tests/test_api_endpoints.py

  docker-build:
    needs: model-testing
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: |
          docker build -t churnguard-api:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker tag churnguard-api:${{ github.sha }} gcr.io/my-project/churnguard-api:latest
          docker push gcr.io/my-project/churnguard-api:latest

  deploy-staging:
    needs: docker-build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Deploy to staging
        run: |
          kubectl set image deployment/churnguard-api \
            churnguard-api=gcr.io/my-project/churnguard-api:${{ github.sha }} \
            --namespace=staging

  deploy-production:
    needs: docker-build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/churnguard-api \
            churnguard-api=gcr.io/my-project/churnguard-api:${{ github.sha }} \
            --namespace=production
      
      - name: Run smoke tests
        run: |
          curl https://api.churnguard.com/health
```

**Docker Configuration:**
```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/models/ ./data/models/
COPY data/processed/scaler.joblib ./data/processed/

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run API server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Lý do trừ điểm:**
- CI/CD is fundamental to MLOps
- Automated testing prevents bugs in production
- Docker enables reproducible deployments
- Industry standard for professional ML systems

**Impact:** -0.2 điểm

---

## 📊 TỔNG HỢP ĐIỂM THIẾU

| # | Vấn đề | Điểm thiếu | Độ khó fix | Thời gian ước tính |
|:--|:-------|:-----------|:-----------|:-------------------|
| 1 | Hyperparameter Tuning | -0.4 | 🟡 Medium | 2-4 giờ |
| 2 | Learning Curves & Analysis | -0.3 | 🟢 Easy | 1-2 giờ |
| 3 | Advanced Data Quality | -0.2 | 🟡 Medium | 2-3 giờ |
| 4 | Monitoring Dashboard | -0.2 | 🔴 Hard | 3-5 giờ |
| 5 | A/B Testing Framework | -0.2 | 🔴 Hard | 3-4 giờ |
| 6 | CI/CD Pipeline | -0.2 | 🔴 Hard | 4-6 giờ |
| **TỔNG** | | **-1.5 điểm** | | **15-24 giờ** |

---

## 🎯 LỘ TRÌNH ĐẠT 10 ĐIỂM

### Phase 1: Quick Wins (4-6 giờ) → 9.2/10.0

**Priority P0 - High Impact, Low Effort:**

1. ✅ **Hyperparameter Tuning** (2-4h)
   ```bash
   # Add Optuna to requirements.txt
   pip install optuna
   
   # Modify train_pipeline.py
   # Add objective() function và study.optimize()
   ```

2. ✅ **Learning Curves** (1-2h)
   ```bash
   # Add to train_pipeline.py hoặc evaluate.py
   # Generate 3-4 charts: learning curves, feature importance, calibration
   ```

**Estimated Score After Phase 1: 9.2/10.0**

---

### Phase 2: Professional Polish (6-8 giờ) → 9.7/10.0

**Priority P1 - Medium Impact:**

3. ✅ **Data Quality Checks** (2-3h)
   ```bash
   pip install great-expectations
   
   # Create expectations/churn_data_suite.json
   # Add validation to preprocess.py
   ```

4. ✅ **Monitoring Dashboard** (3-5h)
   ```bash
   pip install streamlit plotly
   
   # Create dashboard.py
   # Add Prometheus metrics to main.py
   ```

**Estimated Score After Phase 2: 9.7/10.0**

---

### Phase 3: Production Grade (5-10 giờ) → 10.0/10.0

**Priority P2 - Full MLOps:**

5. ✅ **A/B Testing** (3-4h)
   ```bash
   # Add champion/challenger routing
   # Implement analyze_ab_test()
   ```

6. ✅ **CI/CD Pipeline** (4-6h)
   ```bash
   # Create .github/workflows/mlops-pipeline.yml
   # Create Dockerfile
   # Setup pytest tests/
   ```

**Estimated Score After Phase 3: 10.0/10.0** 🏆

---

## ✅ KẾT LUẬN

### Để đạt 10 điểm cần:

**PHẢI LÀM (Critical):**
1. ✅ Hyperparameter tuning với Optuna/GridSearchCV
2. ✅ Learning curves và error analysis
3. ✅ Advanced data quality checks (Great Expectations)

**NÊN LÀM (Important):**
4. ✅ Monitoring dashboard (Streamlit/Prometheus)
5. ✅ A/B testing framework

**BONUS (Nice-to-have):**
6. ✅ Full CI/CD pipeline với GitHub Actions

### Thời gian ước tính:
- **Minimum (đạt 9.2):** 4-6 giờ (Phase 1)
- **Recommended (đạt 9.7):** 10-14 giờ (Phase 1+2)
- **Perfect (đạt 10.0):** 15-24 giờ (All phases)

### Recommendation:
- ✅ **Nếu deadline gấp:** Focus Phase 1 (4-6h) → 9.2 điểm
- ✅ **Nếu có thời gian:** Phase 1+2 (10-14h) → 9.7 điểm
- 🏆 **Nếu muốn perfect:** All phases (15-24h) → 10.0 điểm

**Hiện tại 8.5/10 đã rất tốt để nộp bài. Nhưng nếu muốn 10/10, follow lộ trình trên!** 🎯
