# AST Query Cookbook for AI Coding Assistants

Hướng dẫn chiến lược khai thác Đồ thị AST Graphify để tăng độ chính xác khi phân tích kiến trúc mã nguồn.

## 1. Nguyên Tắc Giảm Tiêu Thụ Token Bằng Graphify
Thay vì đọc 50-100 tệp mã nguồn để hiểu luồng nghiệp vụ:
1. Đọc tóm tắt tại `graphify-out/GRAPH_REPORT.md` để nắm các cụm module (Clusters).
2. Tra cứu `graphify-out/graph.json` để xác định chính xác danh sách các tệp liên quan đến tính năng cần sửa.
3. Chỉ mở và đọc tối đa 3-5 tệp nằm trực tiếp trên đường dẫn gọi hàm (`graphify path`).

## 2. Các Kịch Bản Truy Vấn Thường Gặp

### Kịch bản 1: Thêm trường dữ liệu mới vào Model/Schema
- Chạy `graphify path "UserSchema" "Database"` để xem Schema được dùng ở những đâu.
- Kiểm tra các Controller và Serializer phụ thuộc.

### Kịch bản 2: Tái cấu trúc (Refactoring) Service lõi
- Chạy `graphify god-nodes --top 5` để xem Service đó có phải God Node không.
- Nếu là God Node, chia nhỏ thành các Sub-services hoặc Adapter theo nguyên tắc Single Responsibility.

### Kịch bản 3: Sửa đổi API Contract
- Xác định Frontend Component nào đang tiêu thụ API đó bằng cách kiểm tra các cạnh `fetch` hoặc `axios` trong đồ thị.
