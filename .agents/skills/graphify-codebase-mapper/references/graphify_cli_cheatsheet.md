# Graphify CLI Cheatsheet

Bảng tra cứu nhanh các lệnh thông dụng của công cụ Graphify trong môi trường Windows cmd/powershell.

## 1. Các Lệnh Trích Xuất & Cập Nhật

```bash
# Trích xuất toàn diện AST cục bộ (không tốn token LLM)
cmd /c "graphify extract . --code-only"

# Cập nhật đồ thị khi có tệp bị sửa đổi hoặc thêm mới
cmd /c "graphify update ."

# Buộc quét lại toàn bộ (Full Rescan)
cmd /c "graphify extract . --force --code-only"

# Kiểm tra xem đồ thị có cần cập nhật hay không
cmd /c "graphify check-update ."
```

## 2. Các Lệnh Truy Vấn & Khảo Sát

```bash
# Liệt kê các node trung tâm kiến trúc (God Nodes)
cmd /c "graphify god-nodes --top 10"

# Tìm đường kết nối giữa hai thực thể
cmd /c "graphify path \"ClassOrFileA\" \"ClassOrFileB\""

# Giải thích chi tiết một khái niệm / thành phần
cmd /c "graphify explain \"ComponentName\""

# Xuất cây phân cấp D3 HTML trực quan
cmd /c "graphify tree --output graphify-out/GRAPH_TREE.html"
```

## 3. Quản Lý Hook & Tích Hợp

```bash
# Cài đặt hook đồng bộ tự động với Antigravity IDE
cmd /c "graphify antigravity install"

# Cài đặt git hook tự động cập nhật sau mỗi commit
cmd /c "graphify hook install"
```
