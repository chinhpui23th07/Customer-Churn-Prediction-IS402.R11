# SOP Workflow Templates & Guidelines

Quy chuẩn định dạng các tài liệu Hướng Dẫn Vận Hành Chuẩn (Standard Operating Procedures - SOP) trong thư mục `.agents/workflows/`.

## 1. Cấu Trúc File Workflow Chuẩn

Mỗi file workflow là một cẩm nang chi tiết từng bước (Step-by-Step Runbook) để giải quyết một quy trình kỹ thuật lặp lại:

```markdown
# SOP: [Tên Quy Trình Vận Hành Chuẩn]

## 1. Mục Tiêu & Phạm Vi (Objective & Scope)
- Mục tiêu cần đạt được khi kết thúc workflow.
- Điều kiện tiên quyết (Prerequisites).

## 2. Quy Trình Thực Thi Từng Bước (Step-by-Step SOP)

### Bước 1: [Tên Bước 1]
- Mô tả hành động cụ thể.
- Lệnh shell hoặc tool call cần thực hiện.

### Bước 2: [Tên Bước 2]
- Xử lý dữ liệu và logic nghiệp vụ.
- Kiểm tra tính toàn vẹn.

### Bước 3: [Tên Bước 3]
- Bàn giao và nghiệm thu.

## 3. Ma Trận Xử Lý Sự Cố (Troubleshooting & Escalation)
Bảng tra cứu nếu gặp lỗi trong quá trình thực hiện quy trình:
| Hiện Tượng Lỗi | Nguyên Nhân Gốc Rễ | Biện Pháp Khắc Phục |
| :--- | :--- | :--- |
| Lỗi A | Nguyên nhân A | Chạy lệnh khắc phục A |

## 4. Danh Mục Kiểm Tra Nghiệm Thu (Acceptance Checklist)
- [ ] Tiêu chí 1 đạt.
- [ ] Tiêu chí 2 đạt.
```
