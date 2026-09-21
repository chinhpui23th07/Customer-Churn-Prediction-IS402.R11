# Firecrawl MCP Cookbook for Autonomous Research

Hướng dẫn chi tiết cách khai thác bộ công cụ Firecrawl MCP để phục vụ tự nghiên cứu và xây dựng giải pháp kỹ thuật.

## 1. Các Công Cụ Sẵn Có

| Công Cụ | Chức Năng | Đầu Vào Khuyên Dùng |
| :--- | :--- | :--- |
| `firecrawl_research_search_papers` | Tìm kiếm bài báo khoa học từ arXiv, PubMed, bioRxiv | `query`: Từ khóa học thuật, `limit`: 3-5 |
| `firecrawl_research_search_github` | Tìm kiếm repository GitHub thực tế | `query`: Tên công nghệ + `best practice` |
| `firecrawl_scrape` | Cào nội dung 1 URL trang web thành Markdown sạch | `url`: Đường dẫn trang tài liệu hoặc bài blog kỹ thuật |
| `firecrawl_crawl` | Thu thập toàn bộ tài liệu từ một tên miền con | `url`: Trang gốc tài liệu thư viện, `limit`: 10-20 |
| `firecrawl_developer_search` | Tìm kiếm thảo luận kỹ thuật của lập trình viên | `query`: Mã lỗi hoặc cấu trúc hàm cụ thể |

## 2. Các Query Mẫu Hiệu Quả Cao

### Tìm bài báo khoa học về Kiến trúc & Thuật toán
```python
# Ví dụ tìm hiểu giải pháp RAG tối ưu
query = "Retrieval Augmented Generation chunking strategies benchmark arXiv"
firecrawl_research_search_papers(query=query, limit=3)
```

### Tìm Repository GitHub chuẩn mực
```python
# Ví dụ tìm repo FastAPI + Next.js Clean Architecture
query = "FastAPI Next.js monorepo clean architecture docker"
firecrawl_research_search_github(query=query, limit=5)
```

### Cào tài liệu thư viện mới nhất
```python
# Cào tài liệu chính thức của thư viện
url = "https://docs.pydantic.dev/latest/concepts/models/"
firecrawl_scrape(url=url)
```
