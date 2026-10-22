"""
Master Orchestrator: Hệ Thống Thanh Tra, Test, Check & Kiểm Định Liêm Chính Học Thuật.
Tập hợp toàn bộ kết quả thanh tra:
- Stub Detector (Mã giả & Tác vụ rỗng)
- Big Data I/O Inspector (Dung lượng dữ liệu & Ngưỡng >4GB)
- Integrity Rubric Auditor (Chấm điểm nghiêm khắc 15 tiêu chí)
Xuất báo cáo ACADEMIC_INTEGRITY_AUDIT_REPORT.md và JSON verdict.
Tuân thủ Invariant 01 và Invariant 02 (< 400 dòng).
"""
import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(BASE_DIR, "scripts", "verification"))

from stub_detector import StubAndIntegrityDetector
from bigdata_io_inspector import audit_current_dataset_size
from integrity_rubric_checker import AcademicIntegrityAuditor

OUTPUT_MD = os.path.join(BASE_DIR, "docs", "ACADEMIC_INTEGRITY_AUDIT_REPORT.md")
OUTPUT_JSON = os.path.join(BASE_DIR, "data", "processed", "academic_inspection_verdict.json")


def run_full_inspection():
    print("=" * 80)
    print("BẮT ĐẦU QUY TRÌNH THANH TRA TOÀN DIỆN LIÊM CHÍNH HỌC THUẬT (IS402 - UIT)")
    print("=" * 80)

    # 1. Chạy Stub Detector
    print("[1/3] Đang thanh tra mã giả, tác vụ rỗng và kiến trúc hạ cấp...")
    stub_detector = StubAndIntegrityDetector()
    stub_report = stub_detector.run_all_audits()
    print(f"      -> Phát hiện {stub_report['critical_violations']} vi phạm nguy cấp, {stub_report['warnings']} cảnh báo.")

    # 2. Chạy Big Data Size Audit
    print("[2/3] Đang thanh tra kích thước dữ liệu đối chiếu ngưỡng >4GB của Rubric 1.3...")
    size_audit = audit_current_dataset_size()
    print(f"      -> Tổng dữ liệu thô: {size_audit['total_raw_mb']} MB ({size_audit['total_raw_gb']} GB).")
    print(f"      -> Trạng thái ngưỡng >4GB: {'ĐẠT CHUẨN' if size_audit['is_compliant_4gb'] else 'VI PHẠM NGHIÊM TRỌNG'}")

    # 3. Chạy Rubric Auditor
    print("[3/3] Đang chấm điểm độc lập 15 tiêu chí theo đúng Rubric môn học...")
    rubric_auditor = AcademicIntegrityAuditor()
    rubric_verdict = rubric_auditor.evaluate_all()
    print(f"      -> ĐIỂM SỐ THỰC TẾ NGHIÊM KHẮC: {rubric_verdict['total_score']} / 10.0")

    # 4. Đóng gói kết quả JSON
    master_verdict = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "real_academic_score": rubric_verdict["total_score"],
        "max_score": 10.0,
        "penalized_points": round(10.0 - rubric_verdict["total_score"], 2),
        "data_size_audit": size_audit,
        "stub_detector_audit": stub_report,
        "rubric_breakdown": rubric_verdict
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(master_verdict, f, indent=2, ensure_ascii=False)

    # 5. Xuất báo cáo Markdown chi tiết
    md_content = f"""# BÁO CÁO THANH TRA ĐỘC LẬP VÀ KIỂM ĐỊNH LIÊM CHÍNH HỌC THUẬT

> **Thời điểm thanh tra:** {master_verdict['timestamp']}  
> **Cơ quan thẩm định:** Ban Thanh tra & Đảm bảo Chất lượng Đồ án MLOps (IS402 - UIT)  
> **Kết luận điểm số thực tế:** **{rubric_verdict['total_score']} / 10.0** (Bị trừ thẳng tay **{master_verdict['penalized_points']} điểm**)

---

## 1. TỔNG QUAN KẾT LUẬN THANH TRA

Hệ thống mã nguồn trên môi trường local **đã được hoàn thiện đầy đủ khung logic kỹ thuật** (4 thuật toán ML, Optuna Bayesian tuning, SHAP explainability, FastAPI serving, Feast dual-store SQLite/Redis fallback, Evidently AI drift detector, Web Bento Grid). 

Tuy nhiên, đối chiếu với **Rubric chấm điểm chính thức của Giảng viên (ThS. Hà Lê Hoài Trung)** cho môn Điện toán đám mây (IS402), hệ thống bị trừ điểm nghiêm ngặt (**-{master_verdict['penalized_points']} điểm**) do **hoàn toàn chưa kết nối hạ tầng Cloud Azure thực tế**:

1. **Giới hạn Kích thước dữ liệu trên máy cục bộ (Mục 1.3):** Dữ liệu thô trên ổ đĩa local chỉ đạt **{size_audit['total_raw_mb']} MB ({size_audit['total_raw_gb']} GB)**, thiếu hụt gấp **{size_audit['deficit_factor']} lần** so với ngưỡng >4GB của đề tài. Kịch bản Big Data Cloud đã được đóng gói sẵn tại `notebooks/rees46_bigdata_cloud_benchmark.ipynb` (tập 5.28 GB, 42.45M dòng) chờ thực thi trên môi trường Cloud.
2. **Lưu trữ Cloud Storage (Mục 3.2):** Pipeline ETL streaming đã sẵn sàng adapter `sync_to_cloud_storage` nhưng hiện chỉ ghi vào `data/processed/` cục bộ do chưa có Azure Blob Connection String.
3. **Đo độ trễ Multi-Region (Mục 3.3):** Kịch bản `latency_simulator.py` đã đo đạc RTT mạng TCP tới 5 Azure Region công cộng, nhưng chưa dựng cụm máy ảo tính toán riêng biệt tại từng Region.
4. **Hạ tầng Feature Store Online (Mục 3.4):** Feast Online Store đang vận hành ở chế độ SQLite local fallback; adapter kết nối Redis SSL cổng 6380 đã hoàn thiện trong `feature_store.py` nhưng chưa có cụm Azure Cache for Redis live.
5. **Thiên kiến dữ liệu huấn luyện (Mục 4.1):** Dữ liệu Kaggle tổng hợp có quy luật tất định (hợp đồng Monthly churn 99.84%), dẫn đến ROC-AUC đạt mức cao tuyệt đối (>0.999).
6. **Môi trường Quản trị Cloud & Quotas (Mục 5.4):** Các kịch bản IaC (ARM, Terraform, Container Apps, `deploy_azure.bat`) và bảng tính TCO $90.75/tháng đã hoàn tất, nhưng chưa gắn với live Azure Subscription.

---

## 2. BẢNG ĐIỂM CHI TIẾT 15 TIÊU CHÍ THEO RUBRIC CHÍNH THỨC

| STT | Tiêu chí Rubric | Điểm Max | Điểm Thực | Lý do trừ điểm & Bằng chứng thực nghiệm |
| :---: | :--- | :---: | :---: | :--- |
| **1.1** | Phân loại bài toán | 0.25đ | **{rubric_verdict['scores_by_criterion']['1.1']}đ** | Đạt: Phân loại đúng bài toán xử lý, dự đoán. |
| **1.2** | Loại dữ liệu | 0.25đ | **{rubric_verdict['scores_by_criterion']['1.2']}đ** | Đạt: Dữ liệu dạng bảng (Tabular Dataset 13 đặc trưng). |
| **1.3** | Kích thước & So sánh tốc độ xử lý | 0.75đ | **{rubric_verdict['scores_by_criterion']['1.3']}đ** | **{rubric_verdict['penalties'].get('1.3', '')}** |
| **1.4** | Phân loại thành phần Cloud | 0.25đ | **{rubric_verdict['scores_by_criterion']['1.4']}đ** | {rubric_verdict['penalties'].get('1.4', '')} |
| **2.1** | Cơ sở định dạng lưu trữ | 0.50đ | **{rubric_verdict['scores_by_criterion']['2.1']}đ** | {rubric_verdict['penalties'].get('2.1', '')} |
| **2.2** | Cơ sở thuật toán xử lý | 0.50đ | **{rubric_verdict['scores_by_criterion']['2.2']}đ** | {rubric_verdict['penalties'].get('2.2', '')} |
| **2.3** | Chi tiết các dịch vụ Cloud | 0.50đ | **{rubric_verdict['scores_by_criterion']['2.3']}đ** | {rubric_verdict['penalties'].get('2.3', '')} |
| **3.1** | Tốc độ cho phép đọc ghi | 0.50đ | **{rubric_verdict['scores_by_criterion']['3.1']}đ** | {rubric_verdict['penalties'].get('3.1', '')} |
| **3.2** | Thiết lập luồng tự động ETL | 0.50đ | **{rubric_verdict['scores_by_criterion']['3.2']}đ** | **{rubric_verdict['penalties'].get('3.2', '')}** |
| **3.3** | Đo độ trễ đặt server ở region khác | 0.50đ | **{rubric_verdict['scores_by_criterion']['3.3']}đ** | **{rubric_verdict['penalties'].get('3.3', '')}** |
| **3.4** | Giải pháp tối ưu hóa đọc ghi | 0.50đ | **{rubric_verdict['scores_by_criterion']['3.4']}đ** | **{rubric_verdict['penalties'].get('3.4', '')}** |
| **4.1** | Huấn luyện model trên dữ liệu | 1.00đ | **{rubric_verdict['scores_by_criterion']['4.1']}đ** | {rubric_verdict['penalties'].get('4.1', '')} |
| **4.2** | Cung cấp cơ chế API cho model | 0.50đ | **{rubric_verdict['scores_by_criterion']['4.2']}đ** | {rubric_verdict['penalties'].get('4.2', '')} |
| **4.3** | Trực quan hóa kết quả model | 1.00đ | **{rubric_verdict['scores_by_criterion']['4.3']}đ** | **{rubric_verdict['penalties'].get('4.3', '')}** |
| **4.4** | Viết trang web sử dụng API model | 0.50đ | **{rubric_verdict['scores_by_criterion']['4.4']}đ** | {rubric_verdict['penalties'].get('4.4', '')} |
| **5.1** | Slide PowerPoint báo cáo | 0.50đ | **{rubric_verdict['scores_by_criterion']['5.1']}đ** | {rubric_verdict['penalties'].get('5.1', '')} |
| **5.2** | Báo cáo Word KLTN | 0.50đ | **{rubric_verdict['scores_by_criterion']['5.2']}đ** | {rubric_verdict['penalties'].get('5.2', '')} |
| **5.3** | Thuyết trình & Demo | 0.50đ | **{rubric_verdict['scores_by_criterion']['5.3']}đ** | Chưa diễn ra buổi bảo vệ trực tiếp trước Hội đồng. |
| **5.4** | Quản lý dự án trên Cloud & Quotas | 0.50đ | **{rubric_verdict['scores_by_criterion']['5.4']}đ** | **{rubric_verdict['penalties'].get('5.4', '')}** |
| **TỔNG**| **ĐIỂM TOÀN HỆ THỐNG** | **10.0đ** | **{rubric_verdict['total_score']} / 10.0đ** | **BỊ TRỪ {master_verdict['penalized_points']} ĐIỂM DO THIẾU CLOUD THẬT** |

---

## 3. DANH MỤC BẰNG CHỨNG VI PHẠM KỸ THUẬT (STUBS & ARCHITECTURAL GAPS)

```json
{json.dumps(stub_report['findings'], indent=2, ensure_ascii=False)}
```

---

## 4. KẾ HOẠCH HÀNH ĐỘNG KHẮC PHỤC TRIỆT ĐỂ (ACTION PLAN TO 10.0)

1. **Khắc phục Kích thước dữ liệu (>4GB):** Khởi chạy `notebooks/rees46_bigdata_cloud_benchmark.ipynb` trên Kaggle Cloud GPU/CPU với tập dữ liệu 5.28 GB để thu thập số liệu I/O thực tế phục vụ báo cáo.
2. **Khắc phục Storage Cloud:** Cung cấp thông tin tài khoản Azure Storage để DVC và hàm `sync_to_cloud_storage` đẩy dữ liệu lên Azure Blob Storage container.
3. **Khắc phục Feature Store:** Triển khai Azure Cache for Redis và cấu hình `AZURE_REDIS_CONNECTION_STRING` để Feast Online Store chuyển sang Redis In-Memory.
4. **Khắc phục Triển khai Cloud:** Chạy `deploy/azure/deploy_azure.bat` với tài khoản Azure sinh viên để khởi tạo Azure Container Apps serving public URL.
5. **Khắc phục Buổi bảo vệ:** Thực hiện thuyết trình slide và demo toàn bộ kịch bản 4 Tiers trước Giảng viên hướng dẫn để thu trọn điểm số mục 5.3.
"""

    os.makedirs(os.path.dirname(OUTPUT_MD), exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n[+] ĐÃ XUẤT BÁO CÁO THANH TRA TOÀN DIỆN VÀO:")
    print(f"    - Markdown Report: {OUTPUT_MD}")
    print(f"    - JSON Verdict:   {OUTPUT_JSON}")
    print("=" * 80)
    return master_verdict


if __name__ == "__main__":
    run_full_inspection()
