# Rule Template Standards for Antigravity Ecosystem

Quy chuẩn định dạng và siêu dữ liệu (Frontmatter) bắt buộc khi tạo rule mới trong `.agents/rules/`.

## 1. Cấu Trúc YAML Frontmatter Chuẩn

Mỗi file rule `.md` phải bắt đầu bằng khối YAML frontmatter:
```yaml
---
id: rule-<so_thu_tu_hoac_ten_ngan>
title: <Tieu de ro rang cua rule>
activation: <always_on | model_decision | glob>
globs: "<danh_sach_file_ap_dung_neu_dung_glob>" # Tuy chon
description: "<Tom tat ngan gon 1-2 cau ve muc dich va pham vi cua rule>"
---
```

### Các Giá Trị `activation` Hỗ Trợ:
- `always_on`: Luôn được nạp vào system prompt trong mọi lượt trao đổi.
- `model_decision`: Agent tự đánh giá tính liên quan với yêu cầu hiện tại để nạp.
- `glob`: Tự động kích hoạt khi người dùng làm việc với các file khớp pattern (ví dụ: `src/contracts/**/*.sol`).

## 2. Các Mục Bắt Buộc Trong Thân Rule

```markdown
# Rule: [Tên Quy Chuẩn]

## 1. Mục Đích & Nguyên Tắc Vận Hành
Mô tả lý do vì sao quy chuẩn này tồn tại và giá trị bảo vệ hệ thống.

## 2. Các Ràng Buộc Kỹ Thuật Chi Tiết (Technical Constraints)
Đặc tả chi tiết các tiêu chuẩn, giới hạn, và kiến trúc bắt buộc tuân theo.

## 3. Anti-Pattern vs Positive Pattern (So Sánh Sai - Đúng)
Sử dụng khối `diff` để chỉ rõ lỗi sai thường gặp và cách sửa chuẩn mực:
```diff
- // ANTI-PATTERN: Viết sai
+ // POSITIVE PATTERN: Viết đúng
```

## 4. Lệnh Kiểm Tra Đối Kháng Tự Động (Verification Assertions)
Cung cấp ít nhất 1-2 lệnh shell để kiểm tra xem rule có bị vi phạm không:
```bash
cmd /c "<lenh_kiem_tra>"
```
```
