# Design System Specification: Google Stitch UI - ChurnGuard MLOps

> **System Standard:** Google Stitch Semantic Design Specification  
> **Aesthetic Profile:** Oceanic Navy, Natural Deep Slate, Warm Amber & Emerald  
> **Anti-AI Policy:** Tuyệt đối không sử dụng dải màu tím-đen AI cliché. Tất cả icon đều là SVG vector bespoke hoặc Lucide. Ký tự gạch ngang chuẩn bàn phím `-`.

---

## 1. Color Palette (Bảng Màu Tự Nhiên)

| Vai trò Token | Tên Màu | Giá trị Hex | Giá trị HSL | Mục đích Sử dụng |
| :--- | :--- | :--- | :--- | :--- |
| `color-bg-primary` | Deep Midnight Ocean | `#0A192F` | `hsl(216, 65%, 11%)` | Nền chính của toàn bộ trang dashboard |
| `color-bg-surface` | Slate Elevation 1 | `#112240` | `hsl(218, 58%, 16%)` | Nền thẻ Bento Card cơ bản |
| `color-bg-surface-elevated` | Slate Elevation 2 | `#1E3A5F` | `hsl(214, 52%, 24%)` | Nền thẻ khi hover hoặc card nổi bật |
| `color-border` | Subtle Ocean Border | `#233554` | `hsl(218, 41%, 23%)` | Đường viền phân cách card |
| `color-border-hover` | Active Ocean Border | `#38BDF8` | `hsl(199, 89%, 60%)` | Viền khi active hoặc focus |
| `color-accent-primary` | Warm Sun Amber | `#F59E0B` | `hsl(38, 92%, 50%)` | Màu nhấn hành động chính, CTA buttons |
| `color-accent-secondary` | Deep Teal Emerald | `#0F766E` | `hsl(175, 77%, 26%)` | Màu bổ trợ cho các chỉ số ổn định |
| `color-status-success` | Vivid Emerald | `#10B981` | `hsl(160, 84%, 39%)` | Trạng thái khách hàng an toàn (Low Churn Risk) |
| `color-status-warning` | Marigold Warning | `#FBBF24` | `hsl(43, 96%, 56%)` | Khách hàng nguy cơ trung bình (Medium Risk) |
| `color-status-danger` | Coral Crimson | `#EF4444` | `hsl(0, 84%, 60%)` | Khách hàng nguy cơ cao rời bỏ (High Risk) |
| `color-text-primary` | Crisp Ice White | `#F8FAFC` | `hsl(210, 40%, 98%)` | Tiêu đề chính và thông tin quan trọng |
| `color-text-secondary` | Muted Silver Slate | `#94A3B8` | `hsl(215, 20%, 65%)` | Nhãn phụ, mô tả tính năng |
| `color-text-muted` | Darkened Blue Gray | `#64748B` | `hsl(215, 16%, 47%)` | Placeholder, timestamps |

---

## 2. Typography & Hierarchy (Google Fonts: Inter & Outfit)

- **Font chữ Tiêu đề (Headings):** `'Outfit', -apple-system, BlinkMacSystemFont, sans-serif`
  - `H1 (Page Title):` 32px / 700 weight / letter-spacing: -0.02em
  - `H2 (Section Header):` 22px / 600 weight / letter-spacing: -0.01em
  - `H3 (Card Title):` 17px / 600 weight
- **Font chữ Nội dung & Data (Body & Numbers):** `'Inter', -apple-system, BlinkMacSystemFont, sans-serif`
  - `Body Normal:` 14px / 400 weight / line-height: 1.5
  - `Data Metrics / Stat Numbers:` 26px / 700 weight / tabular-nums
  - `Captions & Labels:` 12px / 500 weight / letter-spacing: 0.05em (UPPERCASE)

---

## 3. Surface Elevation & Glassmorphism Tokens

- **Card Radius:** `14px` đồng nhất trên toàn hệ thống.
- **Card Shadow:** `0 8px 32px 0 rgba(2, 8, 20, 0.37)`.
- **Glassmorphism Effect:**
  - `background: rgba(17, 34, 64, 0.75);`
  - `backdrop-filter: blur(12px);`
  - `-webkit-backdrop-filter: blur(12px);`
  - `border: 1px solid rgba(56, 189, 248, 0.12);`

---

## 4. Bento Grid Layout Structure

Dashboard áp dụng bố cục **Bento Grid 12 cột** linh hoạt:
1. **Hero KPI Row (12 Cột):** 4 thẻ chỉ số nhanh (Model Accuracy/ROC-AUC, Feast Feature Count, Total Predictions, Drift Status).
2. **Interactive Core (Hai Cột Chính):**
   - **Cột Trái (5 Cột): Single Customer Realtime Prediction Form**
     - Form nhập liệu thông minh (Tuổi, Giới tính, Thời hạn hợp đồng, Số cuộc gọi hỗ trợ, Số tiền chi tiêu, Độ trễ thanh toán).
     - Đồng hồ đo rủi ro trực quan (Risk Gauge) với màu sắc chuyển động tương ứng.
     - Hộp đề xuất giải pháp giữ chân khách hàng (Actionable Retention Strategy).
   - **Cột Phải (7 Cột): Batch Processing & Model Analytics**
     - **Tab 1: Batch Prediction:** Drag-and-drop file CSV, phân tích hàng nghìn khách hàng, thống kê tỷ lệ rời bỏ và cho phép tải báo cáo CSV đã gắn nhãn rủi ro.
     - **Tab 2: Model Benchmark:** So sánh 4 thuật toán (Logistic Regression, Random Forest, XGBoost, LightGBM) với biểu đồ trực quan.
     - **Tab 3: Evidently Drift Monitor:** Trực quan phân phối đặc trưng (Feature Distribution Drift) và phát hiện lệch dữ liệu.

---

## 5. Micro-Animations & Interactivity

- **Button Hover:** Transform `translateY(-2px)` kết hợp `box-shadow: 0 4px 14px rgba(245, 158, 11, 0.35)`.
- **Card Hover:** Viền sáng chuyển từ `rgba(56, 189, 248, 0.12)` sang `rgba(56, 189, 248, 0.35)`.
- **Transitions:** `all 0.25s cubic-bezier(0.4, 0, 0.2, 1)`.
