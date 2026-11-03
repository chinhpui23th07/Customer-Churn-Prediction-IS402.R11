# API contract v0.1 — historical KKBox churn replay

Endpoint mục tiêu: `POST /v1/predictions`. Body JSON:

```json
{
  "subscriber_key": "1234567890123456789",
  "as_of_date": "2017-02-28"
}
```

ID trong ví dụ chỉ minh họa, không đảm bảo tồn tại trong dataset. `subscriber_key` là **string** số thập phân (không gửi JSON number để tránh mất chính xác 64 bit trong JavaScript). `as_of_date` bắt buộc và chỉ nhận `2017-01-31` hoặc `2017-02-28` khi demo lịch sử. API tạo `snapshot_key` nội bộ từ ID và cutoff để lấy đúng snapshot Feast online, dùng model alias `champion` đã huấn luyện trên feature cùng phiên bản. Không nhận `is_churn` trong request; không trả nhãn thật trong response.

Response thành công `200`:

```json
{
  "subscriber_key": "1234567890123456789",
  "as_of_date": "2017-02-28",
  "prediction": 1,
  "churn_probability": 0.73,
  "risk_level": "high",
  "model_version": "<MLflow version>",
  "feature_version": "kkbox-v1",
  "prediction_mode": "historical_replay"
}
```

`prediction` là 0/1; `churn_probability` thuộc [0,1]. Ngưỡng phân loại và ngưỡng `risk_level` phải lưu cùng model, chọn bằng validation tháng 02, không cố định 0.5 hoặc các ngưỡng rủi ro khi chưa đánh giá. `model_version` phải là phiên bản thực sự đã nạp. Không trả `recommended_action` như tác động nhân quả chưa được chứng minh.

Lỗi: `422` cho khóa/cutoff sai định dạng hoặc cutoff ngoài danh sách; `404` khi không có snapshot khách hàng đúng cutoff; `503` khi model hoặc feature store chưa sẵn sàng. Không trả dự đoán giả nếu thiếu dữ liệu. Auth dùng secret cấu hình môi trường; không hardcode khóa trong web công khai.

Endpoint mới `POST /v1/predictions` đã chạy trên pilot ở `src/kkbox/api.py`; trang `/demo` nhập ID, chọn cutoff và gọi API. API mặc định dùng Feast online store; model pilot chỉ được bật với `KKBOX_ALLOW_PILOT=1`. API Kaggle cũ ở `src/api/main.py` vẫn tồn tại để đối chiếu. Endpoint batch mới `POST /v1/predictions/batch` còn cần triển khai sau khi single prediction trên full data được kiểm chứng.
