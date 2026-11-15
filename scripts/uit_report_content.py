"""
Dữ liệu chuẩn học thuật và hàm định dạng cho Báo Cáo Khóa Luận / Đồ Án UIT.
"""
import os
import json
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

UIT_FRONT_MATTER = {
    "ministry": "BỘ GIÁO DỤC VÀ ĐÀO TẠO",
    "vnuhcm": "ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH",
    "univ": "TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN",
    "faculty": "KHOA HỆ THỐNG THÔNG TIN",
    "report_type": "BÁO CÁO NGHIÊN CỨU & TRIỂN KHAI KỸ THUẬT MLOPS DOANH NGHIỆP",
    "thesis_type": "CÔNG TRÌNH NGHIÊN CỨU & TRIỂN KHAI THỰC TẾ",
    "major": "CHUYÊN NGÀNH: HỆ THỐNG THÔNG TIN & ĐIỆN TOÁN ĐÁM MÂY",
    "course_name": "HỆ THỐNG MLOPS CẤP ĐỘ DOANH NGHIỆP (ENTERPRISE MLOPS LEVEL 2)",
    "title_vi": "MLOPS - XÂY DỰNG HỆ THỐNG DỰ ĐOÁN KHÁCH HÀNG RỜI BỎ DỊCH VỤ (CUSTOMER CHURN PREDICTION)",
    "title_en": "ENTERPRISE MLOPS LEVEL 2 PLATFORM FOR REAL-TIME CUSTOMER CHURN PREDICTION AND DATA DRIFT MONITORING",
    "instructor_title": "CÁN BỘ HƯỚNG DẪN:",
    "instructor_name": "ThS. HÀ LÊ HOÀI TRUNG",
    "reviewer_title": "CÁN BỘ PHẢN BIỆN:",
    "reviewer_name": "QUÝ THẦY/CÔ HỘI ĐỒNG BỘ MÔN",
    "student_header": "NHÓM NGHIÊN CỨU KỸ THUẬT:",
    "student_name": "[Để trống / Tác giả bảo mật]",
    "student_id": "[Để trống / Tác giả bảo mật]",
    "class_name": "HỆ THỐNG THÔNG TIN",
    "cohort": "PHIÊN BẢN DOANH NGHIỆP 2026",
    "location": "TP. HỒ CHÍ MINH, THÁNG 09 NĂM 2026",
    "decision_number": "Biên bản thẩm định kỹ thuật và nghiệm thu kiến trúc ChurnGuard Enterprise MLOps Level 2 năm 2026.",
    "pledge": (
        "Nhóm nghiên cứu xin cam đoan đây là công trình nghiên cứu khoa học và triển khai kỹ thuật thực tế "
        "dưới sự hướng dẫn khoa học của ThS. Hà Lê Hoài Trung. Toàn bộ mã nguồn, dữ liệu thực nghiệm chính thức trên tập KKBox "
        "(7.52 GB, 32 tệp Parquet Zstd, 442,211,685 bản ghi gốc, lát cắt thực thi DuckDB 37,629,251 -> 970,960 bản ghi sạch) cùng bộ kiểm chuẩn "
        "hồi quy 442,211 bản ghi duy nhất, các mô hình học máy, kho lưu trữ đặc trưng Feast Feature Store và hệ thống giám sát trôi dạt dữ liệu "
        "đều được cài đặt, huấn luyện và kiểm thử thực tế trên máy trạm và hạ tầng đám mây.\n\n"
        "Các số liệu và kết quả trình bày trong báo cáo là hoàn toàn trung thực, khách quan và có thể tái lập 100%. "
        "Mọi sự tham khảo từ các công trình nghiên cứu khoa học quốc tế giai đoạn 2024 - 2026, các kho mã nguồn mở uy tín trên GitHub "
        "và báo giá đối chuẩn từ 6 nhà cung cấp đám mây (Azure, AWS, GCP, OCI, OVHcloud, DigitalOcean) đều được trích dẫn nguồn gốc rõ ràng theo quy chuẩn IEEE."
    ),
    "acknowledgments": (
        "Lời đầu tiên, nhóm nghiên cứu xin bày tỏ lòng biết ơn sâu sắc và chân thành nhất đến ThS. Hà Lê Hoài Trung - Cán bộ hướng dẫn "
        "khoa học tại Trường Đại học Công nghệ Thông tin - ĐHQG-HCM, Thầy đã tận tình truyền đạt kiến thức "
        "chuyên sâu về hạ tầng đám mây, kiến trúc phân tán và định hướng nghiên cứu quý báu trong suốt quá trình thực hiện đề tài.\n\n"
        "Nhóm nghiên cứu cũng xin trân trọng cảm ơn Quý Thầy/Cô Khoa Hệ thống Thông tin đã tạo điều kiện và trang bị nền tảng kiến thức "
        "về cơ sở dữ liệu, phân tích dữ liệu lớn và quy trình phát triển phần mềm chuẩn mực.\n\n"
        "Đồng thời, nhóm xin gửi lời cảm ơn chân thành đến cộng đồng mã nguồn mở quốc tế (các dự án Feast, MLflow, Optuna, Evidently AI, "
        "FastAPI, Scikit-learn, XGBoost, LightGBM) và các tác giả của những công trình nghiên cứu khoa học tiên phong giai đoạn 2024 - 2026 "
        "đã chia sẻ các tri thức nền tảng vô giá giúp công trình đạt được độ hoàn thiện công nghệ cao nhất."
    ),
    "abstract_vi": (
        "Trong nền kinh tế số và thị trường dịch vụ định kỳ cạnh tranh cao, việc chủ động dự đoán nguy cơ khách hàng rời bỏ dịch vụ "
        "(Customer Churn) là bài toán chiến lược quyết định hiệu quả giữ chân và tối ưu hóa lợi nhuận (e-Profits & CATE Uplift). "
        "Công trình thiết kế và triển khai nền tảng ChurnGuard MLOps Level 2, giải quyết hai thách thức sản xuất: lệch pha đặc trưng "
        "(Training-Serving Skew) qua Feast Dual-Store và suy giảm mô hình do biến động phân phối qua bộ đo Normalized Wasserstein + Midpoint PSI.\n\n"
        "Trên tuyến dữ liệu lớn thực nghiệm KKBox (7.52 GB, 442,211,685 bản ghi gốc nén Zstandard), công cụ DuckDB Out-of-Core (giới hạn RAM <= 2 GB) "
        "xử lý phân vùng 37,629,251 bản ghi thô xuống 970,960 hồ sơ thuê bao trong 5.61 giây (nhanh gấp 15.06x so với CSV). Mô hình chủ lực "
        "KKBox_LGBM_Champion đạt ROC-AUC 0.8764, PR-AUC 0.5947, Accuracy 93.31% và Brier Score 0.05312 (5-Fold CV 0.8775 +- 0.0014), song hành cùng "
        "bộ kiểm chuẩn hồi quy 442,211 bản ghi (XGBoost ROC-AUC 0.9990). Hạ tầng Azure Managed Redis Balanced B0 (Port 10000) / Valkey 8.0 "
        "được đối chuẩn qua Infracost ở mức $70.61/tháng (Baseline IaC) và $11.22/tháng (Serverless Scale-to-Zero) với 100% Checkov IAC pass (28/28)."
    ),
    "abstract_en": (
        "In the subscription-based digital economy, proactive customer churn prediction is critical for retention economics and Customer Lifetime Value. "
        "This engineering work implements ChurnGuard, an enterprise MLOps Level 2 platform eliminating Training-Serving Skew via Feast Dual-Store "
        "and mitigating distribution drift using Normalized Wasserstein Distance and Midpoint-smoothed PSI coupled with automated retraining hooks.\n\n"
        "Evaluated on the primary KKBox subscription dataset (7.52 GB, 32 Zstd Parquet files, 442,211,685 raw rows), bounded-memory DuckDB ETL (<= 2 GB) "
        "processes a 37,629,251-row partition into 970,960 curated subscribers in 5.61 seconds (15.06x faster than CSV). KKBox_LGBM_Champion achieves "
        "ROC-AUC 0.8764, PR-AUC 0.5947, Accuracy 0.9331, and Brier Score 0.05312 (5-Fold CV 0.8775 +- 0.0014), complemented by a preserved 442,211-row "
        "regression benchmark track (XGBoost ROC-AUC 0.9990). Multi-cloud FinOps grounded across 6 providers validates Azure IaC baseline at $70.61/month "
        "and Serverless Scale-to-Zero at $11.22/month using Azure Managed Redis Balanced B0 / Valkey 8.0 with 28/28 Checkov IaC checks passing."
    ),
    "keywords_vi": "MLOps, Dự đoán Churn, Feature Store, Feast, MLflow, Data Drift, Evidently AI, Tối ưu Optuna, SHAP XAI, Điện toán Đám mây.",
    "keywords_en": "MLOps, Customer Churn Prediction, Feature Store, Feast, MLflow, Data Drift, Evidently AI, Optuna Tuning, Explainable AI, Cloud Computing."
}

ABBREVIATIONS_LIST = [
    ("1", "MLOps", "Machine Learning Operations", "Tập hợp các quy chuẩn tự động hóa vận hành vòng đời học máy"),
    ("2", "CI/CD", "Continuous Integration / Continuous Delivery", "Tích hợp liên tục và Chuyển giao liên tục mã nguồn"),
    ("3", "CT", "Continuous Training", "Cơ chế tự động kích hoạt tái huấn luyện mô hình khi có Drift"),
    ("4", "DVC", "Data Version Control", "Hệ thống quản lý phiên bản dữ liệu và tái lập quy trình huấn luyện"),
    ("5", "ROC-AUC", "Receiver Operating Characteristic - Area Under Curve", "Diện tích dưới đường cong ROC đánh giá độ phân biệt lớp"),
    ("6", "PR-AUC", "Precision-Recall Area Under Curve", "Diện tích dưới đường cong Precision-Recall cho dữ liệu mất cân bằng"),
    ("7", "PSI", "Population Stability Index", "Chỉ số ổn định phân phối dữ liệu đo lường mức độ biến dịch phân phối"),
    ("8", "KS-test", "Kolmogorov-Smirnov Test", "Kiểm định thống kê phi tham số so sánh phân phối hai mẫu"),
    ("9", "SHAP", "SHapley Additive exPlanations", "Phương pháp giải thích mức độ đóng góp đặc trưng dựa trên lý thuyết trò chơi"),
    ("10", "TCO", "Total Cost of Ownership", "Tổng chi phí sở hữu hạ tầng phần cứng, mạng và dịch vụ đám mây"),
    ("11", "REST API", "Representational State Transfer API", "Giao diện lập trình ứng dụng truyền tải dữ liệu theo giao thức HTTP"),
    ("12", "ACID", "Atomicity, Consistency, Isolation, Durability", "Bốn thuộc tính bảo đảm độ tin cậy và toàn vẹn giao dịch cơ sở dữ liệu")
]

IEEE_REFERENCES_LIST = [
    "[1] M. A. Hasan et al., 'Enhancing Customer Churn Prediction in Telecommunications: An Adaptive Ensemble Learning Approach,' arXiv:2408.16284, 2024.",
    "[2] F. Bodria, F. Giannotti, and D. Pedreschi, 'From XAI to MLOps: Explainable Concept Drift Detection with Profile Drift Detection,' arXiv:2412.11308, 2024.",
    "[3] A. Manzoor, M. A. Qureshi, E. Kidney, and L. Longo, 'e-Profits: A Profit-Driven Metric for Customer Churn Prediction and Targeted Retention Campaigns,' arXiv:2507.08860, 2025.",
    "[4] S. Verma, K. Patel, and R. Kumar, 'Explainability, Risk Modeling, and Segmentation Based Customer Churn Analytics for Personalized Retention,' arXiv:2510.11604, 2025.",
    "[5] J. Zhang et al., 'A Multi-Criteria Automated MLOps Pipeline for Cost-Effective Cloud-Based Classifier Retraining in Response to Data Distribution Shifts,' arXiv:2512.11541, 2025.",
    "[6] M. Weber, H. Schmidt, and L. Wagner, 'Ethical and Explainable AI in Reusable MLOps Pipelines,' arXiv:2603.03341, 2026.",
    "[7] D. Kreuzberger, N. Kuhl, and S. Hirschl, 'Machine Learning Operations (MLOps): Overview, Definition, and Architecture,' IEEE Access, vol. 11, pp. 31866-31879, 2023.",
    "[8] Feast Development Team, 'Feast: Feature Store for Production Machine Learning Deployment,' 2025. [Online]. Available: https://feast.dev",
    "[9] Evidently AI, 'Continuous Drift Monitoring & Model Evaluation in Production Systems,' 2025. [Online]. Available: https://evidentlyai.com",
    "[10] T. Akiba et al., 'Optuna: A Next-generation Hyperparameter Optimization Framework,' in Proc. ACM SIGKDD, 2019, pp. 2623-2631."
]

FIGURES_LIST = [
    ("Hình 1.1", "Sơ đồ tổng quan kiến trúc hệ thống ChurnGuard MLOps", "2"),
    ("Hình 2.1", "Quản lý vòng đời mô hình và Versioning với MLflow", "3"),
    ("Hình 2.2", "Quy trình quản lý phiên bản dữ liệu với DVC", "4"),
    ("Hình 2.3", "Kiến trúc Dual-Store của Feast Feature Store", "4"),
    ("Hình 3.1", "Luồng cấu hình dự đoán mô hình Serving Pipeline", "6"),
    ("Hình 3.2", "Thiết kế luồng xử lý suy luận thời gian thực qua REST API", "6"),
    ("Hình 3.3", "Thiết kế cơ chế giám sát độ trôi dạt dữ liệu Monitor Drift", "6"),
    ("Hình 3.4", "Kiến trúc CI/CD Pipeline tự động hóa với GitHub Actions", "6"),
    ("Hình 3.5", "Mô hình Self-hosted Runner an toàn trong CI/CD", "6"),
    ("Hình 4.1", "Quá trình hội tụ tối ưu hóa siêu tham số bằng Optuna qua 12 trials", "8"),
    ("Hình 4.2", "Biểu đồ so sánh trực quan các chỉ số hiệu năng 4 mô hình học máy", "8"),
    ("Hình 4.3", "Đường cong học tập (Learning Curves) xác nhận không bị quá khớp", "9"),
    ("Hình 4.4", "Ma trận nhầm lẫn (Confusion Matrix) trên tập kiểm thử Holdout", "9"),
    ("Hình 4.5", "Mức độ quan trọng của các đặc trưng theo mô hình XGBoost", "9"),
    ("Hình 4.6", "Biểu đồ phân tích lỗi phân loại sâu (Error Analysis)", "9")
]

TABLES_LIST = [
    ("Bảng 3.1", "So sánh các mô hình dịch vụ đám mây (IaaS, PaaS, FaaS, SaaS) trong MLOps", "5"),
    ("Bảng 4.1", "Kết quả kiểm định chất lượng dữ liệu với 10 Data Contracts Great Expectations", "7"),
    ("Bảng 4.2", "So sánh hiệu năng tổng hợp của 4 mô hình trên kiểm định 5-Fold CV và Test Holdout", "8"),
    ("Bảng 4.3", "Bộ siêu tham số tối ưu đạt được qua 12 trials bằng Optuna TPE Sampler", "8"),
    ("Bảng 5.1", "Kết quả thử nghiệm hiệu năng I/O (KKBox DuckDB Big Data và Parquet vs CSV vs SQLite)", "10"),
    ("Bảng 5.2", "Kết quả đo kiểm độ trễ mạng thực tế từ Client đến các Cloud Regions", "10"),
    ("Bảng 5.3", "Dự toán tổng chi phí sở hữu hạ tầng đám mây (TCO) hàng tháng trên Microsoft Azure", "11"),
    ("Bảng 5.4", "Định mức hạn ngạch tài nguyên (Quotas) và cấu hình cảnh báo ngân sách trên Azure", "11"),
    ("Bảng 5.5", "Phân chia vai trò thành viên nhóm và ma trận phân quyền IAM RBAC trên Azure", "12")
]


def set_cell_shading(cell, color_hex):
    """Đặt màu nền cho ô bảng Word."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)


def set_table_borders(table, color="000000", sz="4", col_widths=None):
    """Thêm đường kẻ khung viền bảng đen chuẩn học thuật, căn full lề 16.0cm và chống vỡ dòng."""
    tblPr = table._tbl.tblPr
    for w in tblPr.xpath('./w:tblW'):
        tblPr.remove(w)
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:w'), '9072')  # 9072 dxa = 16.0 cm = Inches(6.30)
    tblW.set(qn('w:type'), 'dxa')
    tblPr.append(tblW)

    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right']:
        b = OxmlElement(f'w:{border_name}')
        b.set(qn('w:val'), 'single')
        b.set(qn('w:sz'), '6')
        b.set(qn('w:space'), '0')
        b.set(qn('w:color'), color)
        tblBorders.append(b)
    for border_name in ['insideH', 'insideV']:
        b = OxmlElement(f'w:{border_name}')
        b.set(qn('w:val'), 'single')
        b.set(qn('w:sz'), sz)
        b.set(qn('w:space'), '0')
        b.set(qn('w:color'), color)
        tblBorders.append(b)
    tblPr.append(tblBorders)

    if len(table.rows) > 0:
        trPr0 = table.rows[0]._tr.get_or_add_trPr()
        trPr0.append(OxmlElement('w:tblHeader'))
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement('w:cantSplit'))

    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                if i < len(row.cells):
                    row.cells[i].width = w


def format_table_cell(cell, text="", bold=False, italic=False, font_size=10,
                      align=WD_ALIGN_PARAGRAPH.LEFT, color_rgb=None, fill_hex=None):
    """Định dạng ô bảng tuân thủ chuẩn học thuật: Times New Roman 10-11pt, dãn dòng 1.25."""
    if fill_hex:
        set_cell_shading(cell, fill_hex)
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.text = ""
    r = p.add_run(str(text))
    r.font.name = 'Times New Roman'
    r.font.size = Pt(font_size)
    r.font.bold = bold
    r.font.italic = italic
    if color_rgb:
        r.font.color.rgb = color_rgb
    else:
        r.font.color.rgb = RGBColor(0, 0, 0)


def add_uit_body_p(doc, text, bold_prefix=None, first_line_indent=True):
    """
    Thêm đoạn văn chuẩn UIT:
    - Font: Times New Roman, 13pt
    - Line spacing: 1.5 lines
    - Space before: 0pt, Space after: 6pt
    - First line indent: 1.0 cm (Inches(0.39))
    - Alignment: JUSTIFY (Căn đều hai bên)
    Tự động tách các đoạn ngăn bởi newline để triệt tiêu hoàn toàn hiện tượng thưa chữ khi căn đều trong Word.
    """
    paragraphs = [p.strip() for p in str(text).split("\n") if p.strip()]
    last_p = None
    first = True
    for para in paragraphs:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        if first_line_indent:
            p.paragraph_format.first_line_indent = Inches(0.39)

        if first and bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(13)
            r_pre.font.bold = True

        r = p.add_run(para)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(0, 0, 0)
        first = False
        last_p = p
    return last_p


def add_uit_heading_1(doc, text):
    """Thêm tiêu đề Chương chuẩn UIT: In hoa, đậm 14pt."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.5
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0, 0, 0)
    return p


def add_uit_heading_2(doc, text):
    """Thêm tiêu đề mục cấp 2 (1.1): Đậm 13pt, căn trái."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.5
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
    r.font.bold = True
    return p


def add_uit_heading_3(doc, text):
    """Thêm tiêu đề mục cấp 3 (1.1.1): Đậm nghiêng 13pt, căn trái."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.5
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.italic = True
    return p


def add_uit_figure(doc, images_dir, filename, caption_text, width_in_inches=3.8):
    """Thêm hình ảnh chuẩn UIT: Căn giữa, tên hình đặt DƯỚI hình, Times New Roman 11pt nghiêng."""
    img_path = os.path.join(images_dir, filename)
    if os.path.exists(img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.paragraph_format.keep_with_next = True
        run_img = p_img.add_run()
        run_img.add_picture(img_path, width=Inches(width_in_inches))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(6)
        r_cap = p_cap.add_run(caption_text)
        r_cap.font.name = 'Times New Roman'
        r_cap.font.size = Pt(11)
        r_cap.font.italic = True


def add_uit_figures_side_by_side(doc, images_dir, f1, c1, f2, c2, w_in_inches=2.9):
    """Thêm 2 hình ảnh song song (2 cột) chuẩn UIT với bảng không viền."""
    p1 = os.path.join(images_dir, f1)
    p2 = os.path.join(images_dir, f2)
    if os.path.exists(p1) and os.path.exists(p2):
        tbl = doc.add_table(rows=1, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblPr = tbl._tbl.tblPr
        tblBorders = OxmlElement('w:tblBorders')
        for b_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
            b = OxmlElement(f'w:{b_name}')
            b.set(qn('w:val'), 'none')
            tblBorders.append(b)
        tblPr.append(tblBorders)

        cell0 = tbl.rows[0].cells[0]
        cell0.width = Inches(3.1)
        p0 = cell0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after = Pt(2)
        p0.paragraph_format.keep_with_next = True
        p0.add_run().add_picture(p1, width=Inches(w_in_inches))
        p0_c = cell0.add_paragraph()
        p0_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0_c.paragraph_format.space_before = Pt(2)
        p0_c.paragraph_format.space_after = Pt(4)
        r0 = p0_c.add_run(c1)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(10)
        r0.font.italic = True

        cell1 = tbl.rows[0].cells[1]
        cell1.width = Inches(3.1)
        p1_g = cell1.paragraphs[0]
        p1_g.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1_g.paragraph_format.space_before = Pt(2)
        p1_g.paragraph_format.space_after = Pt(2)
        p1_g.paragraph_format.keep_with_next = True
        p1_g.add_run().add_picture(p2, width=Inches(w_in_inches))
        p1_c = cell1.add_paragraph()
        p1_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1_c.paragraph_format.space_before = Pt(2)
        p1_c.paragraph_format.space_after = Pt(4)
        r1 = p1_c.add_run(c2)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(10)
        r1.font.italic = True


def load_json_data(filepath):
    """Hàm tải dữ liệu từ artifact JSON."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
