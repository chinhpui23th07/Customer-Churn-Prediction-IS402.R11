# Debugging Search Patterns & Query Cheat Sheet

Bảng tổng hợp cú pháp tìm kiếm lỗi lập trình hiệu quả cao trên Google, StackOverflow và GitHub Issues:

## 1. Cú Pháp Tìm Kiếm Theo Từng Ngôn Ngữ & Framework

| Công Nghệ | Dạng Lỗi Thường Gặp | Cú Pháp Tìm Kiếm Chuẩn Mực |
| :--- | :--- | :--- |
| **React / Next.js** | Lỗi Hydration | `site:stackoverflow.com "Text content does not match server-rendered HTML" "next.js"` |
| **React** | Infinite Re-render Loop | `site:stackoverflow.com "Too many re-renders. React limits the number of renders" "useEffect"` |
| **Python / FastAPI** | Pydantic v2 Validation | `site:stackoverflow.com "pydantic.errors.PydanticUserError" "v2" "model_validator"` |
| **PyTorch / AI** | Device Mismatch | `site:stackoverflow.com "Expected all tensors to be on the same device" "cuda" "pytorch"` |
| **Solidity / Hardhat** | Transaction Reverted | `site:ethereum.stackexchange.com "Transaction reverted without a reason string" "hardhat"` |
| **Docker** | Port Binding / Network | `site:stackoverflow.com "Bind for 0.0.0.0:8000 failed: port is already allocated"` |
| **Node.js / ESM** | Module Not Found | `site:stackoverflow.com "ERR_MODULE_NOT_FOUND" "type module" "package.json"` |
| **TypeScript** | Type Not Assignable | `site:stackoverflow.com "Type '...' is not assignable to type '...'" "generic"` |

## 2. Các Tiêu Chí Đánh Giá Câu Trả Lời Tin Cậy
1. **Có lời giải thích rõ ràng cơ chế hoạt động:** Tránh những câu trả lời chỉ ghi "thử dòng code này xem". Ưu tiên câu trả lời phân tích vì sao bug phát sinh.
2. **Phiên bản tương đồng:** Kiểm tra xem câu trả lời viết cho phiên bản nào (ví dụ React 18+ vs React 16, Python 3.10+ vs Python 2).
3. **Cộng đồng đồng thuận:** Tỷ lệ upvotes áp đảo so với các câu trả lời khác.
