"""
Unit tests for Milestone 5: Causal Uplift (CATE) Meta-Learners, Decision Theory & Academic Citations.

Grounding:
Awais Manzoor, M. Atif Qureshi, Etain Kidney, and Luca Longo (TU Dublin / UCC, Ireland),
"e-Profits: A Profit-Driven Metric for Customer Churn Prediction and Targeted Retention Campaigns",
arXiv:2507.08860 (2025).
"""

import os
import pytest
import numpy as np
from src.economics.retention_optimizer import (
    MetaLearnerType,
    CustomerQuadrant,
    SLearner,
    TLearner,
    XLearner,
    compute_cate_uplift,
    segment_customers_by_uplift,
    compute_optimal_retention_threshold,
    compute_expected_retention_profit,
    compute_cate_expected_profit,
    compute_optimal_cate_threshold,
    generate_recommendation as econ_generate_recommendation,
)
from src.api.utils import (
    compute_optimal_retention_threshold as utils_compute_threshold,
    compute_expected_retention_profit as utils_compute_profit,
    generate_recommendation as utils_generate_recommendation,
)


@pytest.fixture
def synthetic_uplift_data():
    """Generate reproducible synthetic training data for causal meta-learners."""
    np.random.seed(42)
    n = 200
    d = 4
    X = np.random.randn(n, d)
    W = np.random.binomial(1, 0.5, size=n)
    base_risk = 1.0 / (1.0 + np.exp(-(X[:, 0] * 0.8 + X[:, 1] * 0.5)))
    treated_risk = np.clip(base_risk - 0.20, 0.0, 1.0)
    probs = np.where(W == 1, treated_risk, base_risk)
    y = np.random.binomial(1, probs)
    return X, y, W


def test_meta_learner_enums():
    """Verify that MetaLearnerType and CustomerQuadrant enums contain canonical values."""
    assert MetaLearnerType.S_LEARNER.value == "s_learner"
    assert MetaLearnerType.T_LEARNER.value == "t_learner"
    assert MetaLearnerType.X_LEARNER.value == "x_learner"

    assert CustomerQuadrant.PERSUADABLES.value == "Persuadables"
    assert CustomerQuadrant.LOST_CAUSES.value == "Lost Causes"
    assert CustomerQuadrant.SURE_THINGS.value == "Sure Things"
    assert CustomerQuadrant.SLEEPING_DOGS.value == "Sleeping Dogs"


def test_s_learner_fit_and_predict(synthetic_uplift_data):
    """Test S-Learner uplift estimation pipeline."""
    X, y, W = synthetic_uplift_data
    s_learner = SLearner()
    s_learner.fit(X, y, W)

    uplifts = s_learner.predict_uplift(X[:10])
    assert isinstance(uplifts, np.ndarray)
    assert len(uplifts) == 10
    single_uplift = s_learner.predict_uplift(X[0])
    assert isinstance(single_uplift, float)


def test_t_learner_fit_and_predict(synthetic_uplift_data):
    """Test T-Learner uplift estimation pipeline."""
    X, y, W = synthetic_uplift_data
    t_learner = TLearner()
    t_learner.fit(X, y, W)

    uplifts = t_learner.predict_uplift(X[:10])
    assert isinstance(uplifts, np.ndarray)
    assert len(uplifts) == 10
    single_uplift = t_learner.predict_uplift(X[0])
    assert isinstance(single_uplift, float)


def test_x_learner_fit_and_predict(synthetic_uplift_data):
    """Test X-Learner crossover imputed effect estimation pipeline."""
    X, y, W = synthetic_uplift_data
    x_learner = XLearner()
    x_learner.fit(X, y, W)

    uplifts = x_learner.predict_uplift(X[:10])
    assert isinstance(uplifts, np.ndarray)
    assert len(uplifts) == 10
    single_uplift = x_learner.predict_uplift(X[0])
    assert isinstance(single_uplift, float)


def test_compute_cate_uplift_functional(synthetic_uplift_data):
    """Test compute_cate_uplift functional API with both probabilities and fitted model."""
    assert round(compute_cate_uplift(0.75, 0.45), 4) == 0.30
    assert round(compute_cate_uplift(0.30, 0.50), 4) == -0.20

    X, y, W = synthetic_uplift_data
    t_learner = TLearner().fit(X, y, W)
    uplift = compute_cate_uplift(None, None, model=t_learner, x_input=X[:5])
    assert len(uplift) == 5


def test_four_quadrant_segmentation_scalar():
    """Test 4-quadrant customer segmentation on individual profiles."""
    assert segment_customers_by_uplift(uplift=0.18, baseline_churn=0.70) == CustomerQuadrant.PERSUADABLES.value
    assert segment_customers_by_uplift(uplift=-0.08, baseline_churn=0.40) == CustomerQuadrant.SLEEPING_DOGS.value
    assert segment_customers_by_uplift(uplift=0.02, baseline_churn=0.85) == CustomerQuadrant.LOST_CAUSES.value
    assert segment_customers_by_uplift(uplift=0.01, baseline_churn=0.15) == CustomerQuadrant.SURE_THINGS.value


def test_four_quadrant_segmentation_vectorized():
    """Test 4-quadrant customer segmentation on batch arrays."""
    uplifts = np.array([0.25, -0.12, 0.02, 0.01])
    baselines = np.array([0.80, 0.35, 0.90, 0.10])
    expected = [
        CustomerQuadrant.PERSUADABLES.value,
        CustomerQuadrant.SLEEPING_DOGS.value,
        CustomerQuadrant.LOST_CAUSES.value,
        CustomerQuadrant.SURE_THINGS.value,
    ]
    results = segment_customers_by_uplift(uplift=uplifts, baseline_churn=baselines)
    assert results == expected


def test_decision_theory_economics():
    """Verify e-Profits decision rules, optimal thresholds, and profit calculations."""
    p_star = compute_optimal_retention_threshold(residual_clv=200.0, cost_offer=15.0, alpha_lift=0.25)
    assert round(p_star, 4) == 0.30

    assert compute_optimal_retention_threshold(residual_clv=0.0) == 1.0
    assert compute_optimal_retention_threshold(residual_clv=-100.0) == 1.0
    assert compute_optimal_retention_threshold(residual_clv=200.0, alpha_lift=0.0) == 1.0

    profit = compute_expected_retention_profit(prob=0.80, residual_clv=200.0, cost_offer=15.0, alpha_lift=0.25)
    assert profit == 25.0
    assert compute_expected_retention_profit(prob=0.80, residual_clv=-50.0) == -15.0

    cate_profit = compute_cate_expected_profit(cate_uplift=0.20, residual_clv=200.0, cost_offer=15.0)
    assert cate_profit == 25.0
    sleeping_dog_profit = compute_cate_expected_profit(cate_uplift=-0.10, residual_clv=200.0, cost_offer=15.0)
    assert sleeping_dog_profit == -35.0

    tau_star = compute_optimal_cate_threshold(residual_clv=200.0, cost_offer=15.0)
    assert round(tau_star, 4) == 0.075
    assert compute_optimal_cate_threshold(residual_clv=0.0) == float("inf")


def test_utils_backward_compatibility():
    """Ensure src/api/utils.py seamlessly re-exports functions with identical behavior."""
    assert utils_compute_threshold(residual_clv=200.0) == compute_optimal_retention_threshold(residual_clv=200.0)
    assert utils_compute_profit(prob=0.80, residual_clv=200.0) == compute_expected_retention_profit(prob=0.80, residual_clv=200.0)

    rec1 = utils_generate_recommendation(prob=0.85, calls=5, delay=8, total_spend=800.0, residual_clv=350.0)
    rec2 = econ_generate_recommendation(prob=0.85, calls=5, delay=8, total_spend=800.0, residual_clv=350.0)
    assert rec1 == rec2
    assert "ƯU TIÊN KHẨN CẤP" in rec1 or "RỦI RO CAO" in rec1

    rec_sleeping = econ_generate_recommendation(prob=0.8, calls=1, delay=1, quadrant=CustomerQuadrant.SLEEPING_DOGS.value)
    assert "KHÔNG CAN THIỆP" in rec_sleeping

    rec_sure = econ_generate_recommendation(prob=0.2, calls=0, delay=0, quadrant=CustomerQuadrant.SURE_THINGS.value)
    assert "DUY TRÌ TIÊU CHUẨN" in rec_sure

    rec_lost = econ_generate_recommendation(prob=0.9, calls=1, delay=1, quadrant=CustomerQuadrant.LOST_CAUSES.value)
    assert "TỐI THIỂU CHI PHÍ" in rec_lost


def test_academic_citation_correctness():
    """Audit project documentation and scripts for correct Awais Manzoor et al. attribution."""
    base_dir = os.path.dirname(os.path.dirname(__file__))

    handbook_path = os.path.join(base_dir, "docs", "specifications", "MASTER_PROJECT_TECHNICAL_HANDBOOK.md")
    with open(handbook_path, "r", encoding="utf-8") as f:
        handbook_content = f.read()
    assert "Awais Manzoor, M. Atif Qureshi, Etain Kidney, and Luca Longo" in handbook_content
    assert "Emaad Manzoor" not in handbook_content

    uit_report_path = os.path.join(base_dir, "scripts", "uit_report_content.py")
    with open(uit_report_path, "r", encoding="utf-8") as f:
        uit_content = f.read()
    assert "A. Manzoor, M. A. Qureshi, E. Kidney, and L. Longo" in uit_content
    assert "Y. Chen et al., 'e-Profits" not in uit_content

    slides_path = os.path.join(base_dir, "scripts", "generate_pptx_slides.py")
    with open(slides_path, "r", encoding="utf-8") as f:
        slides_content = f.read()
    assert "Awais Manzoor et al." in slides_content
    assert "Chen et al. (2025 - arXiv:2507.08860)" not in slides_content
