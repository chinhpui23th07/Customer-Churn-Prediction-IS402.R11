#!/usr/bin/env python
"""
Kiểm tra và thẩm định toàn diện các bản sửa lỗi hệ thống (System Fixes Verification)
"""
import sys
import os
import json
import pandas as pd
import numpy as np
import joblib
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.append('src')

print("=" * 80)
print("KIỂM TRA KỸ CÀNG CÁC FIXES")
print("=" * 80)

# ==================== CHECK 1: Dataset Bias Analysis ====================
print("\n[1] KIỂM TRA DATASET BIAS ANALYSIS")
print("-" * 80)
bias_file = 'data/processed/dataset_bias_analysis.json'
if os.path.exists(bias_file):
    with open(bias_file) as f:
        bias = json.load(f)
    
    print("✅ File tồn tại: dataset_bias_analysis.json")
    print("\nContract Length Distribution:")
    
    for contract, stats in bias.get('contract_length_distribution', {}).items():
        churn_rate = stats.get('churn_rate', 0)
        total = stats.get('total_customers', 0)
        churned = stats.get('churned_count', int(total * churn_rate))
        retained = stats.get('retained_count', total - churned)
        
        print(f"\n  {contract}:")
        print(f"    - Churn Rate: {churn_rate:.4f} ({churn_rate*100:.2f}%)")
        print(f"    - Total Customers: {total:,}")
        print(f"    - Churned: {churned:,}")
        print(f"    - Retained: {retained:,}")
    
    # Check for Monthly bias
    monthly = bias.get('contract_length_distribution', {}).get('Monthly', {})
    if monthly.get('churn_rate', 0) > 0.99:
        print(f"\n  🚨 CRITICAL: Monthly contracts = {monthly['churn_rate']*100:.2f}% churn!")
        print("  This explains ROC-AUC = 0.999 (deterministic rule in dataset)")
else:
    print("❌ File không tồn tại: dataset_bias_analysis.json")

# ==================== CHECK 2: Model Metrics & Cross-Validation ====================
print("\n\n[2] KIỂM TRA MODEL METRICS & CROSS-VALIDATION")
print("-" * 80)
model_path = 'data/models/champion_model.joblib'
if os.path.exists(model_path):
    model_artifact = joblib.load(model_path)
    
    print(f"✅ Model type: {type(model_artifact['model']).__name__}")
    print(f"\nTest Set Metrics:")
    for key, val in model_artifact['metrics'].items():
        print(f"  {key}: {val}")
    
    # Check CV
    if 'cv_roc_auc_mean' in model_artifact:
        print(f"\n✅ Cross-Validation Results:")
        print(f"  CV ROC-AUC: {model_artifact['cv_roc_auc_mean']:.4f} ± {model_artifact.get('cv_roc_auc_std', 0):.4f}")
        cv_f1 = model_artifact.get('cv_f1_mean', None)
        if cv_f1:
            print(f"  CV F1:      {cv_f1:.4f} ± {model_artifact.get('cv_f1_std', 0):.4f}")
    else:
        print("\n❌ KHÔNG CÓ: Cross-validation results missing!")
else:
    print("❌ Model file không tồn tại")

# ==================== CHECK 3: Feast Timestamp Logic ====================
print("\n\n[3] KIỂM TRA FEAST TIMESTAMP LOGIC")
print("-" * 80)
feast_file = 'data/processed/train_features.parquet'
if os.path.exists(feast_file):
    df = pd.read_parquet(feast_file)
    
    print(f"Total rows: {len(df):,}")
    print(f"Columns: {list(df.columns)}")
    
    if 'event_timestamp' in df.columns:
        unique_timestamps = df['event_timestamp'].nunique()
        print(f"Unique event_timestamp values: {unique_timestamps:,}")
        
        if unique_timestamps == 1:
            print("\n❌ LỖI: All rows have SAME timestamp!")
            print(f"   Timestamp: {df['event_timestamp'].iloc[0]}")
            print("   Feast time-travel queries will NOT work")
        else:
            print(f"\n✅ OK: {unique_timestamps:,} unique timestamps")
            print(f"   Min: {df['event_timestamp'].min()}")
            print(f"   Max: {df['event_timestamp'].max()}")
    else:
        print("\n❌ KHÔNG CÓ: 'event_timestamp' column missing!")
        print("   Feast requires event_timestamp for time-travel queries")
else:
    print("❌ File không tồn tại: train_features.parquet")

# ==================== CHECK 4: Enum Validation ====================
print("\n\n[4] KIỂM TRA ENUM VALIDATION")
print("-" * 80)
try:
    from api.schemas import CustomerInput
    from pydantic import ValidationError
    
    # Test valid input
    try:
        c = CustomerInput(
            age=25, gender='Male', tenure=12, usage_frequency=5,
            support_calls=2, payment_delay=1, last_interaction=30,
            subscription_type='Premium', contract_length='Monthly', total_spend=500
        )
        print("✅ Test 1 PASSED: Valid enums accepted")
    except ValidationError as e:
        print(f"❌ Test 1 FAILED: {e}")
    
    # Test invalid gender
    try:
        c = CustomerInput(
            age=25, gender='Apache Helicopter', tenure=12, usage_frequency=5,
            support_calls=2, payment_delay=1, last_interaction=30,
            subscription_type='Premium', contract_length='Monthly', total_spend=500
        )
        print("❌ Test 2 FAILED: Invalid gender should be rejected!")
    except ValidationError:
        print("✅ Test 2 PASSED: Invalid gender rejected")
    
    # Test invalid subscription
    try:
        c = CustomerInput(
            age=25, gender='Male', tenure=12, usage_frequency=5,
            support_calls=2, payment_delay=1, last_interaction=30,
            subscription_type='UltraMega', contract_length='Monthly', total_spend=500
        )
        print("❌ Test 3 FAILED: Invalid subscription should be rejected!")
    except ValidationError:
        print("✅ Test 3 PASSED: Invalid subscription rejected")
        
except Exception as e:
    print(f"❌ ERROR: {e}")

# ==================== CHECK 5: SHAP Implementation ====================
print("\n\n[5] KIỂM TRA SHAP IMPLEMENTATION")
print("-" * 80)
if os.path.exists('src/api/utils.py'):
    print("✅ File tồn tại: src/api/utils.py")
    
    # Check for shap import
    with open('src/api/utils.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'import shap' in content or 'from shap' in content:
        print("✅ SHAP library được import")
    else:
        print("❌ KHÔNG CÓ: SHAP import missing")
    
    if 'TreeExplainer' in content:
        print("✅ TreeExplainer được sử dụng")
    else:
        print("❌ KHÔNG CÓ: TreeExplainer not found")
    
    if 'shap_values' in content:
        print("✅ SHAP values được tính toán")
    else:
        print("❌ KHÔNG CÓ: shap_values calculation missing")
else:
    print("❌ File không tồn tại: src/api/utils.py")

# ==================== CHECK 6: Drift Detection Logic ====================
print("\n\n[6] KIỂM TRA DRIFT DETECTION LOGIC")
print("-" * 80)
drift_file = 'src/monitoring/drift_detector.py'
if os.path.exists(drift_file):
    with open(drift_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check what files are being compared
    if 'val_features.parquet' in content and 'test_features.parquet' in content:
        print("❌ LỖI: Still comparing VAL vs TEST!")
        print("   Should compare: TRAIN vs PRODUCTION")
        print("   Current: val_features.parquet vs test_features.parquet")
        print("   Both are from SAME dataset split → Always no drift")
    elif 'train_features.parquet' in content and 'production' in content.lower():
        print("✅ OK: Comparing TRAIN vs PRODUCTION")
    else:
        print("⚠️  Cannot determine drift comparison logic")
else:
    print("❌ File không tồn tại")

# ==================== CHECK 7: PSI Calculation ====================
print("\n\n[7] KIỂM TRA PSI CALCULATION")
print("-" * 80)
if os.path.exists(drift_file):
    with open(drift_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'min(np.min(expected), np.min(actual))' in content:
        print("❌ LỖI: PSI uses COMBINED min/max (wrong formula)")
        print("   Should use: np.percentile(expected, ...) for bins")
    elif 'np.percentile(expected' in content:
        print("✅ OK: PSI uses correct percentile-based bins")
    else:
        print("⚠️  Cannot verify PSI calculation method")
else:
    print("❌ File không tồn tại")

# ==================== CHECK 8: API Authentication ====================
print("\n\n[8] KIỂM TRA API AUTHENTICATION")
print("-" * 80)
if os.path.exists('src/api/utils.py'):
    with open('src/api/utils.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'verify_api_key' in content:
        print("✅ API key verification function exists")
    else:
        print("❌ KHÔNG CÓ: verify_api_key function missing")
    
    if 'X-API-Key' in content or 'x_api_key' in content:
        print("✅ API key header check present")
    else:
        print("❌ KHÔNG CÓ: API key header check missing")
else:
    print("❌ File không tồn tại")

# ==================== CHECK 9: Customer ID Isolation ====================
print("\n\n[9] KIỂM TRA CUSTOMER ID ISOLATION")
print("-" * 80)
preprocess_file = 'src/data/preprocess.py'
if os.path.exists(preprocess_file):
    with open(preprocess_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'assert len(train_ids_set & test_ids_set) == 0' in content:
        print("✅ Customer ID leakage check present")
        print("   Validates: No overlap between train/val/test")
    else:
        print("❌ KHÔNG CÓ: Customer ID isolation check missing")
else:
    print("❌ File không tồn tại")

# ==================== CHECK 10: Duplicate Detection ====================
print("\n\n[10] KIỂM TRA DUPLICATE DETECTION")
print("-" * 80)
if os.path.exists(preprocess_file):
    with open(preprocess_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'drop_duplicates' in content and 'customerid' in content:
        print("✅ Duplicate detection present")
        print("   Method: drop_duplicates(subset=['customerid'])")
    else:
        print("❌ KHÔNG CÓ: Duplicate detection missing")
else:
    print("❌ File không tồn tại")

print("\n" + "=" * 80)
print("HOÀN THÀNH KIỂM TRA")
print("=" * 80)
