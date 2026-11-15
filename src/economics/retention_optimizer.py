"""
Retention Optimizer: Decision Theory, CATE Uplift Modeling & Economic Interventions.

Grounding & Academic Foundation:
Awais Manzoor, M. Atif Qureshi, Etain Kidney, and Luca Longo (TU Dublin / UCC, Ireland),
"e-Profits: A Profit-Driven Metric for Customer Churn Prediction and Targeted Retention Campaigns",
arXiv:2507.08860 (2025).

Causal Uplift Meta-Learners: S-Learner, T-Learner, X-Learner (Künzel et al., PNAS 2019).
4-Quadrant Customer Segmentation: Persuadables, Lost Causes, Sure Things, Sleeping Dogs.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression, Ridge


class MetaLearnerType(str, Enum):
    """Supported meta-learner types for CATE uplift modeling."""
    S_LEARNER = "s_learner"
    T_LEARNER = "t_learner"
    X_LEARNER = "x_learner"


class CustomerQuadrant(str, Enum):
    """Four-quadrant customer behavioral segmentation under retention interventions."""
    PERSUADABLES = "Persuadables"
    LOST_CAUSES = "Lost Causes"
    SURE_THINGS = "Sure Things"
    SLEEPING_DOGS = "Sleeping Dogs"


def compute_optimal_retention_threshold(
    residual_clv: float, cost_offer: float = 15.0, alpha_lift: float = 0.25
) -> float:
    """Ex-ante optimal retention threshold (Awais Manzoor et al., arXiv:2507.08860): p_i* = C_offer / (alpha * CLV_i)."""
    if residual_clv <= 0.0 or alpha_lift <= 0.0:
        return 1.0
    return float(np.clip(float(cost_offer) / (float(alpha_lift) * float(residual_clv)), 0.0, 1.0))


def compute_expected_retention_profit(
    prob: float, residual_clv: float, cost_offer: float = 15.0, alpha_lift: float = 0.25
) -> float:
    """Expected retention profit under homogeneous lift alpha: E[Profit_i] = p_i * alpha * CLV_i - C_offer."""
    if residual_clv <= 0.0:
        return -float(cost_offer)
    return float(prob * alpha_lift * residual_clv - cost_offer)


def compute_cate_expected_profit(
    cate_uplift: float, residual_clv: float, cost_offer: float = 15.0
) -> float:
    """Expected retention profit under heterogeneous treatment effect (CATE): E[Profit_i] = tau(X_i) * CLV_i - C_offer."""
    if residual_clv <= 0.0:
        return -float(cost_offer)
    return float(cate_uplift * residual_clv - cost_offer)


def compute_optimal_cate_threshold(residual_clv: float, cost_offer: float = 15.0) -> float:
    """Optimal CATE threshold: tau_i* = C_offer / CLV_i. Target customer i iff tau(X_i) >= tau_i*."""
    return float("inf") if residual_clv <= 0.0 else float(cost_offer / residual_clv)


def compute_cate_uplift(
    control_prob: Any,
    treated_prob: Any = None,
    model: Optional[Any] = None,
    x_input: Optional[Any] = None,
) -> Any:
    """Compute CATE uplift: tau(X) = P(churn | W=0, X) - P(churn | W=1, X)."""
    if model is not None and x_input is not None:
        return model.predict_uplift(x_input)
    if treated_prob is None:
        raise ValueError("treated_prob must be provided if model is None")
    diff = np.asarray(control_prob, dtype=float) - np.asarray(treated_prob, dtype=float)
    return float(diff) if diff.ndim == 0 else diff


def segment_customers_by_uplift(
    uplift: Union[float, List[float], np.ndarray],
    baseline_churn: Optional[Union[float, List[float], np.ndarray]] = None,
    tau_threshold: float = 0.05,
    churn_threshold: float = 0.50,
) -> Union[str, List[str]]:
    """
    Segment customers into 4 quadrants based on CATE uplift tau and baseline churn p_0:
    1. Persuadables: tau >= tau_threshold (stay if treated, churn if untreated).
    2. Sleeping Dogs: tau < 0 (treatment triggers churn!).
    3. Lost Causes: 0 <= tau < tau_threshold and baseline_churn >= churn_threshold.
    4. Sure Things: 0 <= tau < tau_threshold and baseline_churn < churn_threshold.
    """
    is_scalar = isinstance(uplift, (int, float, np.floating))
    u_arr = np.atleast_1d(np.asarray(uplift, dtype=float))
    if baseline_churn is None:
        b_arr = np.full_like(u_arr, 0.50)
    else:
        b_arr = np.atleast_1d(np.asarray(baseline_churn, dtype=float))
        if b_arr.shape != u_arr.shape:
            b_arr = np.broadcast_to(b_arr, u_arr.shape)

    quadrants = []
    for u, b in zip(u_arr, b_arr):
        if u < 0.0:
            quadrants.append(CustomerQuadrant.SLEEPING_DOGS.value)
        elif u >= tau_threshold:
            quadrants.append(CustomerQuadrant.PERSUADABLES.value)
        elif b >= churn_threshold:
            quadrants.append(CustomerQuadrant.LOST_CAUSES.value)
        else:
            quadrants.append(CustomerQuadrant.SURE_THINGS.value)
    return quadrants[0] if is_scalar else quadrants


class BaseMetaLearner:
    """Abstract base class for CATE Uplift Meta-Learners."""
    def fit(self, x: np.ndarray, y: np.ndarray, treatment: np.ndarray) -> "BaseMetaLearner":
        raise NotImplementedError

    def predict_uplift(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class SLearner(BaseMetaLearner):
    """S-Learner (Single Model): estimates mu(X, W); tau(X) = mu(X, W=0) - mu(X, W=1)."""

    def __init__(self, base_model: Optional[Any] = None):
        self.model = base_model if base_model is not None else LogisticRegression(max_iter=1000)

    def fit(self, x: np.ndarray, y: np.ndarray, treatment: np.ndarray) -> "SLearner":
        x_mat = np.asarray(x, dtype=float)
        w_vec = np.asarray(treatment, dtype=float).reshape(-1, 1)
        self.model.fit(np.hstack([x_mat, w_vec]), y)
        return self

    def predict_uplift(self, x: np.ndarray) -> np.ndarray:
        x_mat = np.asarray(x, dtype=float)
        if x_mat.ndim == 1:
            x_mat = x_mat.reshape(1, -1)
        n = x_mat.shape[0]
        x_0 = np.hstack([x_mat, np.zeros((n, 1))])
        x_1 = np.hstack([x_mat, np.ones((n, 1))])
        if hasattr(self.model, "predict_proba"):
            p0 = self.model.predict_proba(x_0)[:, 1]
            p1 = self.model.predict_proba(x_1)[:, 1]
        else:
            p0 = self.model.predict(x_0)
            p1 = self.model.predict(x_1)
        tau = p0 - p1
        return float(tau[0]) if n == 1 else tau


class TLearner(BaseMetaLearner):
    """T-Learner (Two Models): estimates mu_0 on W=0, mu_1 on W=1; tau(X) = mu_0(X) - mu_1(X)."""

    def __init__(self, control_model: Optional[Any] = None, treated_model: Optional[Any] = None):
        self.m0 = control_model if control_model is not None else LogisticRegression(max_iter=1000)
        self.m1 = treated_model if treated_model is not None else LogisticRegression(max_iter=1000)

    def fit(self, x: np.ndarray, y: np.ndarray, treatment: np.ndarray) -> "TLearner":
        x_mat = np.asarray(x, dtype=float)
        y_vec = np.asarray(y, dtype=float)
        w_vec = np.asarray(treatment, dtype=int)
        mask_0, mask_1 = (w_vec == 0), (w_vec == 1)
        if np.sum(mask_0) > 0:
            self.m0.fit(x_mat[mask_0], y_vec[mask_0])
        if np.sum(mask_1) > 0:
            self.m1.fit(x_mat[mask_1], y_vec[mask_1])
        return self

    def predict_uplift(self, x: np.ndarray) -> np.ndarray:
        x_mat = np.asarray(x, dtype=float)
        if x_mat.ndim == 1:
            x_mat = x_mat.reshape(1, -1)
        if hasattr(self.m0, "predict_proba"):
            p0 = self.m0.predict_proba(x_mat)[:, 1]
            p1 = self.m1.predict_proba(x_mat)[:, 1]
        else:
            p0 = self.m0.predict(x_mat)
            p1 = self.m1.predict(x_mat)
        tau = p0 - p1
        return float(tau[0]) if len(tau) == 1 else tau


class XLearner(BaseMetaLearner):
    """X-Learner (Künzel et al. PNAS 2019): Crossover imputed counterfactuals."""

    def __init__(self, base_stage1: Optional[Any] = None, base_stage2: Optional[Any] = None):
        self.m0 = base_stage1 if base_stage1 is not None else LogisticRegression(max_iter=1000)
        self.m1 = clone(self.m0) if base_stage1 is not None else LogisticRegression(max_iter=1000)
        self.tau0 = base_stage2 if base_stage2 is not None else Ridge(alpha=1.0)
        self.tau1 = clone(self.tau0) if base_stage2 is not None else Ridge(alpha=1.0)
        self.propensity_model = LogisticRegression(max_iter=1000)

    def fit(self, x: np.ndarray, y: np.ndarray, treatment: np.ndarray) -> "XLearner":
        x_mat, y_vec, w_vec = np.asarray(x, dtype=float), np.asarray(y, dtype=float), np.asarray(treatment, dtype=int)
        m0_idx, m1_idx = (w_vec == 0), (w_vec == 1)
        self.m0.fit(x_mat[m0_idx], y_vec[m0_idx])
        self.m1.fit(x_mat[m1_idx], y_vec[m1_idx])

        p0_on_1 = self.m0.predict_proba(x_mat[m1_idx])[:, 1] if hasattr(self.m0, "predict_proba") else self.m0.predict(x_mat[m1_idx])
        p1_on_0 = self.m1.predict_proba(x_mat[m0_idx])[:, 1] if hasattr(self.m1, "predict_proba") else self.m1.predict(x_mat[m0_idx])

        self.tau1.fit(x_mat[m1_idx], p0_on_1 - y_vec[m1_idx])
        self.tau0.fit(x_mat[m0_idx], y_vec[m0_idx] - p1_on_0)
        self.propensity_model.fit(x_mat, w_vec)
        return self

    def predict_uplift(self, x: np.ndarray) -> np.ndarray:
        x_mat = np.asarray(x, dtype=float)
        if x_mat.ndim == 1:
            x_mat = x_mat.reshape(1, -1)
        t1_pred = self.tau1.predict(x_mat)
        t0_pred = self.tau0.predict(x_mat)
        e = self.propensity_model.predict_proba(x_mat)[:, 1]
        tau = e * t0_pred + (1.0 - e) * t1_pred
        return float(tau[0]) if len(tau) == 1 else tau


def generate_recommendation(
    prob: float,
    calls: float,
    delay: float,
    total_spend: float = 500.0,
    contract_length: str = "Monthly",
    tenure: float = 12.0,
    residual_clv: Optional[float] = None,
    cate_uplift: Optional[float] = None,
    quadrant: Optional[str] = None,
) -> str:
    """Generate retention intervention recommendations grounded in e-Profits decision theory & CATE uplift."""
    if quadrant is None and cate_uplift is not None:
        quadrant = segment_customers_by_uplift(uplift=cate_uplift, baseline_churn=prob)

    if quadrant == CustomerQuadrant.SLEEPING_DOGS.value:
        return "KHÔNG CAN THIỆP (Sleeping Dogs): Tác động can thiệp gây tác dụng ngược (Uplift âm). Tuyệt đối không gửi ưu đãi để tránh kích hoạt hành vi hủy dịch vụ."
    if quadrant == CustomerQuadrant.SURE_THINGS.value:
        return "DUY TRÌ TIÊU CHUẨN (Sure Things): Khách hàng có xu hướng ở lại tự nhiên mà không cần can thiệp. Tiết kiệm chi phí ưu đãi."
    if quadrant == CustomerQuadrant.LOST_CAUSES.value:
        return "TỐI THIỂU CHI PHÍ (Lost Causes): Rủi ro rời bỏ cao bất kể can thiệp. Đề xuất kênh hỗ trợ tự phục vụ chi phí tối thiểu."

    contract_norm = str(contract_length).strip().capitalize()
    if residual_clv is None:
        monthly_spend = float(total_spend) / max(float(tenure), 1.0)
        est_future_months = 12.0 if contract_norm == "Annual" else (6.0 if contract_norm == "Quarterly" else 3.0)
        future_clv = monthly_spend * est_future_months
    else:
        future_clv = max(float(residual_clv), 0.0)

    is_high_clv = future_clv >= 150.0 or float(total_spend) >= 500.0 or float(tenure) >= 24.0
    is_low_clv = future_clv < 50.0 and float(total_spend) < 200.0

    if prob >= 0.70:
        if is_low_clv:
            return "RỦI RO CAO (CLV Thấp - Tối ưu e-Profits): Gửi thông báo tự động In-App/Email hỗ trợ kỹ thuật và ưu đãi tự phục vụ chi phí thấp để bảo toàn ROI."
        if calls >= 4:
            return f"ƯU TIÊN KHẨN CẤP (CLV Cao ${total_spend:.0f}, Hợp đồng {contract_norm}): Điều động chuyên viên VIP giải quyết khiếu nại kỹ thuật và tặng 1 tháng dịch vụ."
        if delay >= 7:
            return f"RỦI RO CAO (CLV Cao ${total_spend:.0f}): Khách hàng trễ hạn thanh toán. Đề xuất gói chuyển đổi trả góp hoặc giảm giá 20% nâng cấp hợp đồng Annual."
        if contract_norm == "Monthly" and is_high_clv:
            return "RỦI RO CAO (VIP Monthly): Đề xuất chiết khấu 20% chuyển đổi sang hợp đồng Annual kèm gói chăm sóc khách hàng trọng điểm."
        return "RỦI RO CAO: Kích hoạt chương trình chăm sóc VIP và gửi ưu đãi giữ chân cá nhân hóa."

    if prob >= 0.40:
        if is_low_clv:
            return "RỦI RO TRUNG BÌNH (CLV Thấp): Kích hoạt chuỗi Email/In-App hướng dẫn tính năng tự động chi phí thấp (Zero-Touch Retention)."
        if contract_norm == "Monthly":
            return "RỦI RO TRUNG BÌNH: Gửi ưu đãi nâng cấp hợp đồng Quarterly/Annual kèm tặng điểm Loyalty gia hạn sớm."
        return "RỦI RO TRUNG BÌNH: Gửi email giới thiệu tính năng, tặng điểm Loyalty và ưu đãi gia hạn sớm."

    return "KHÁCH HÀNG ỔN ĐỊNH (Low Risk): Duy trì chất lượng dịch vụ tiêu chuẩn và đề xuất chiến dịch Upsell/Cross-sell gói cao cấp khi phù hợp."


def estimate_kaplan_meier_residual_clv(
    monthly_margin: float,
    durations: np.ndarray,
    events: np.ndarray,
    horizon_months: int = 12,
    monthly_discount: float = 0.01,
) -> float:
    """Compute discounted residual CLV via discrete Kaplan-Meier survival S(t) without parametric bias."""
    t_arr = np.asarray(durations, dtype=float)
    e_arr = np.asarray(events, dtype=int)
    if len(t_arr) == 0 or monthly_margin <= 0.0:
        return 0.0
    s_t = 1.0
    residual_clv = 0.0
    for month in range(1, max(1, int(horizon_months)) + 1):
        at_risk = float(np.sum(t_arr >= month))
        if at_risk <= 0.0:
            break
        churned = float(np.sum((t_arr == month) & (e_arr == 1)))
        s_t *= max(0.0, 1.0 - (churned / at_risk))
        residual_clv += float(monthly_margin) * s_t / ((1.0 + monthly_discount) ** month)
    return round(residual_clv, 4)
