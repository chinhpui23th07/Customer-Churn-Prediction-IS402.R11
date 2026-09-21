# Context7 API Patterns & Best Practices

Hướng dẫn truy vấn API documentation chính thức bằng Context7 MCP để loại bỏ hoàn toàn việc dùng sai syntax hoặc API đã bị deprecated.

## 1. Nguyên Tắc 2 Bước Của Context7

### Bước 1: Resolve Library ID
Trước khi tra cứu tài liệu, cần xác định chính xác ID của thư viện trong kho tri thức của Context7:
```json
{
  "ServerName": "context7",
  "ToolName": "resolve-library-id",
  "Arguments": {
    "libraryName": "pydantic"
  }
}
```
Kết quả trả về: ID chính thức của thư viện (ví dụ: `pydantic`, `ethers`, `nextjs`, `fastapi`).

### Bước 2: Query Docs (Tra cứu tài liệu)
Truy vấn trực tiếp cú pháp của class hoặc hàm cần sử dụng:
```json
{
  "ServerName": "context7",
  "ToolName": "query-docs",
  "Arguments": {
    "libraryId": "pydantic",
    "query": "field_validator model_validator v2 syntax"
  }
}
```

## 2. Khi Nào Bắt Buộc Sử Dụng Context7?
1. Khi có sự nhảy vọt phiên bản lớn (Major version bumps): Ví dụ Next.js 14 -> 15, Pydantic v1 -> v2, Ethers v5 -> v6, LangChain 0.1 -> 0.3.
2. Khi gặp lỗi runtime liên quan đến `TypeError: ... is not a function` hoặc `ImportError: cannot import name ...`.
3. Khi viết code TypeScript để đảm bảo tính chuẩn xác của các Type interfaces.
