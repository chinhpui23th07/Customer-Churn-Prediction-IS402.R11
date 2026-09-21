# Google Stitch Prompting & Design Cheatsheet

Hướng dẫn chi tiết phương pháp đặc tả giao diện theo chuẩn mực Google Stitch (Gemini 2.5 Flash UI Engine):

## 1. Cấu Trúc Khung Mô Tả Giao Diện Chuẩn

```
[Loại màn hình / Thành phần] dành cho [Đối tượng người dùng / Bối cảnh]

Các tính năng & Khối thành phần chính:
- [Khối 1: Vị trí, layout, các thẻ con]
- [Khối 2: Bảng dữ liệu, biểu đồ, tương tác]
- [Khối 3: Thao tác nhanh (Quick Actions), bộ lọc]

Phong cách thị giác (Visual Style):
- Bảng màu: [Màu nền chủ đạo, màu phụ, màu điểm nhấn gradient]
- Thẩm mỹ: [Dark Glassmorphic, Modern Bento Grid, Neumorphic, Clean Minimalist]
- Khoảng cách: [Spacious, Balanced, đường viền siêu mảnh, đổ bóng mịn]

Nền tảng & Độ phản hồi: [Responsive Web / Mobile First / Desktop Dashboard]
```

## 2. Ví Dụ Mẫu Áp Dụng Cho Dashboard Nghiệp Vụ

```
Admin Dashboard cho Sàn Giao Dịch Nông Sản Thông Minh (CẠP NÔNG)

Các khối thành phần chính:
- Hàng trên: 4 Thẻ Bento Grid hiển thị Doanh thu ngày, Số HTX tham gia, Sản lượng nông sản, Tỷ lệ giao dịch ký quỹ thành công.
- Khu vực trung tâm: Biểu đồ đường kép (Doanh thu theo thời gian) kết hợp bảng Top 5 nông sản giao dịch nhiều nhất tuần.
- Thanh bên phải (Sidebar Widget): Dòng thời gian thông báo kiểm định chất lượng VietGAP theo thời gian thực.

Phong cách thị giác:
- Nền: Dark Forest Night (#0B130E), thẻ kính mờ (rgba(255,255,255,0.03)) với viền bo tròn 16px.
- Điểm nhấn: Xanh lá mạ Neon (#22C55E) cho trạng thái tích cực và Vàng lúa chín (#EAB308) cho giao dịch đang chờ duyệt.
- Chữ: Font 'Plus Jakarta Sans' cho tiêu đề số liệu, 'Inter' cho bảng biểu chi tiết.
- Tương tác: Hiệu ứng hover nổi nhẹ 2px, shimmer loading skeleton khi tải dữ liệu.
```
