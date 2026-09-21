# Academic Paper Extraction & Synthesis Standard

Quy chuẩn trích xuất tri thức từ các công trình nghiên cứu khoa học phục vụ thiết kế kiến trúc phần mềm và kỹ thuật dữ liệu.

## 1. Cấu Trúc Báo Cáo Nghiên Cứu Chuẩn (Synthesis Document)
Mọi kết quả từ việc đọc paper học thuật thông qua `firecrawl_research_search_papers` hoặc arXiv phải được cô đọng theo cấu trúc Markdown:

```markdown
# [Tên Chủ Đề] - Nghiên Cứu Chuẩn Mực & Đề Xuất Kỹ Thuật

## 1. Bối Cảnh & Động Lực Nghiên Cứu
- Nêu rõ vấn đề kỹ thuật cần giải quyết.
- Các công trình học thuật liên quan (Citations, Authors, Năm công bố).

## 2. Các Thuật Toán & Kiến Trúc Cốt Lõi Được Đề Xuất
- Sơ đồ nguyên lý (ASCII hoặc Mermaid).
- Công thức toán học hoặc quy trình xử lý dữ liệu.
- Định dạng payload và tiêu chuẩn dữ liệu chuẩn hóa.

## 3. Khảo Sát Benchmarks & Đánh Giá Thực Nghiệm
- Thông số đo lường hiệu năng (Latency, Throughput, Gas, Memory, Accuracy).
- Điểm đánh đổi (Trade-offs) và giới hạn kỹ thuật.

## 4. Kế Hoạch Ứng Dụng Vào Dự Án Hiện Tại
- Áp dụng vào module nào?
- Thư viện cần cài đặt.
- Rủi ro kỹ thuật và biện pháp phòng ngừa.
```

## 2. Tiêu Chí Đánh Giá Nguồn Tin Học Thuật
- Ưu tiên các bài báo từ các hội nghị uy tín hàng đầu: IEEE S&P, ACM CCS, USENIX Security, NeurIPS, ICML, VLDB, SIGMOD.
- Ưu tiên các tài liệu tiêu chuẩn chính thức: IETF RFC, NIST Special Publications (SP 800), W3C Recommendations.
