"""
Schema định nghĩa dữ liệu đầu vào và đầu ra cho FastAPI Serving Service.
"""
import math
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, model_validator

MAX_BATCH_SIZE = 1000


class CustomerInput(BaseModel):
    """Dữ liệu đặc trưng của một khách hàng phục vụ dự đoán thời gian thực."""
    customer_id: Optional[int] = Field(default=1, ge=1, description="Customer ID must be >= 1")
    age: float = Field(..., ge=18, le=100, allow_inf_nan=False, description="Tuổi của khách hàng (18-100)", json_schema_extra={"example": 35.0})
    gender: Literal["Female", "Male"] = Field(..., description="Giới tính ('Male' hoặc 'Female')", json_schema_extra={"example": "Female"})
    tenure: float = Field(..., ge=0, le=120, allow_inf_nan=False, description="Thời gian gắn bó với dịch vụ (tháng)", json_schema_extra={"example": 24.0})
    usage_frequency: float = Field(..., ge=0, le=50, allow_inf_nan=False, description="Tần suất sử dụng dịch vụ trong tháng", json_schema_extra={"example": 15.0})
    support_calls: float = Field(..., ge=0, le=30, allow_inf_nan=False, description="Số cuộc gọi yêu cầu hỗ trợ kỹ thuật", json_schema_extra={"example": 3.0})
    payment_delay: float = Field(..., ge=0, le=90, allow_inf_nan=False, description="Số ngày chậm trễ thanh toán hóa đơn", json_schema_extra={"example": 5.0})
    subscription_type: Literal["Basic", "Standard", "Premium"] = Field(..., description="Loại gói cước ('Basic', 'Standard', 'Premium')", json_schema_extra={"example": "Standard"})
    contract_length: Literal["Monthly", "Quarterly", "Annual"] = Field(..., description="Thời hạn hợp đồng ('Monthly', 'Quarterly', 'Annual')", json_schema_extra={"example": "Monthly"})
    total_spend: float = Field(..., ge=0, le=100000, allow_inf_nan=False, description="Tổng số tiền đã chi tiêu (USD)", json_schema_extra={"example": 650.0})
    last_interaction: float = Field(..., ge=0, le=60, allow_inf_nan=False, description="Số ngày kể từ lần tương tác cuối cùng", json_schema_extra={"example": 12.0})

    @model_validator(mode="after")
    def validate_finite_and_customer_id(self) -> "CustomerInput":
        """Kiểm tra toàn bộ trường số thực phải hữu hạn (không chứa NaN/Inf) và customer_id >= 1."""
        if self.customer_id is not None and self.customer_id < 1:
            raise ValueError("customer_id must be >= 1")
        float_fields = (
            "age", "tenure", "usage_frequency", "support_calls",
            "payment_delay", "total_spend", "last_interaction"
        )
        for fname in float_fields:
            val = getattr(self, fname, None)
            if val is not None and (math.isnan(val) or math.isinf(val)):
                raise ValueError(f"Field '{fname}' cannot be NaN or Inf")
        return self


class PredictionResponse(BaseModel):
    """Kết quả dự đoán nguy cơ rời bỏ dịch vụ cho một khách hàng kèm giải thích XAI."""
    customer_id: Optional[int] = None
    churn_prediction: int = Field(..., description="0: Giữ chân (Retained), 1: Rời bỏ (Churned)")
    churn_probability: float = Field(..., description="Xác suất rời bỏ dịch vụ (0.0 đến 1.0)")
    risk_level: str = Field(..., description="Mức độ rủi ro ('Low Risk', 'Medium Risk', 'High Risk')")
    recommended_action: str = Field(..., description="Chiến lược và hành động giữ chân khách hàng đề xuất")
    feature_attributions: Optional[Dict[str, float]] = Field(default=None, description="Tác động đóng góp của từng đặc trưng vào điểm số rời bỏ (SHAP/Feature Attribution)")
    explanation_summary: Optional[str] = Field(default=None, description="Tóm tắt lý do rủi ro chính theo chuẩn XAI")
    model_version: Optional[str] = Field(default="v2.0.0-champion", description="Phiên bản mô hình thực hiện dự đoán")
    latency_ms: float = Field(..., description="Thời gian xử lý dự đoán (milliseconds)")


class BatchPredictionResponse(BaseModel):
    """Kết quả dự đoán hàng loạt cho nhiều khách hàng."""
    total_processed: int
    churn_count: int
    retention_count: int
    overall_churn_rate: float
    risk_distribution: Dict[str, int]
    predictions: List[PredictionResponse]


class HealthResponse(BaseModel):
    """Trạng thái hoạt động của hệ thống phục vụ MLOps."""
    status: str
    champion_model: str
    model_version: str
    feast_online_store: str
    mlflow_tracking_db: str
    uptime_seconds: float
