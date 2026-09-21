"""
Nội dung và cấu trúc chi tiết cho Báo Cáo Khóa Luận / BTL chuẩn UIT.
Chứa các hằng số tiêu chuẩn, danh mục từ viết tắt, tài liệu tham khảo IEEE
và các hàm hỗ trợ định dạng văn bản chuẩn Word UIT.
Tuân thủ Invariant 01 và Invariant 02 (< 400 dòng).
"""
import os
import json
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

UIT_FRONT_MATTER = {
    "univ": "ĐẠI HỌC QUỐC GIA TP. HỒ CHÍ MINH\nTRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN\nKHOA HỆ THỐNG THÔNG TIN",
    "title": "BÁO CÁO ĐỒ ÁN MÔN HỌC: ĐIỆN TOÁN ĐÁM MÂY\nĐỀ TÀI 11: MLOPS - HỆ THỐNG DỰ ĐOÁN KHÁCH HÀNG RỜI BỎ DỊCH VỤ (CUSTOMER CHURN PREDICTION)",
    "course": "Môn học: Điện toán đám mây (Cloud Computing)",
    "instructor": "TS. Nguyễn Trọng Hải",
    "students": "Sinh viên thực hiện: Nguyễn Trọng Khởi (MSSV: 22520695)\nLớp: HTTT2022 - Khóa: 2022 - 2026",
    "location": "TP. HỒ CHÍ MINH, THÁNG 09/2026",
    "pledge": (
        "Tôi xin cam đoan rằng toàn bộ nội dung trong bản báo cáo đồ án này là kết quả nghiên cứu "
        "và thực nghiệm trung thực của cá nhân/nhóm. Toàn bộ mã nguồn, dữ liệu thực nghiệm (442,211 bản ghi "
        "duy nhất sau xử lý khử trùng lặp) và hệ thống MLOps triển khai đều được vận hành thực tế, không sao chép trái phép hay ngụy tạo "
        "dữ liệu giả lập. Các phân tích về giới hạn dữ liệu tổng hợp (synthetic artifacts) và tài liệu tham khảo khoa học quốc tế "
        "đều được trình bày minh bạch theo quy chuẩn IEEE."
    ),
    "acknowledgments": (
        "Lời đầu tiên, chúng em xin trân trọng gửi lời cảm ơn sâu sắc đến TS. Nguyễn Trọng Hải cùng Quý Thầy/Cô Bộ môn "
        "môn học Điện toán Đám mây tại Trường Đại học Công nghệ Thông tin - ĐHQG-HCM đã truyền đạt kiến thức nền tảng quý báu "
        "và định hướng học thuật trong suốt quá trình thực hiện đề tài.\n\n"
        "Đồng thời, chúng em xin gửi lời cảm ơn đến cộng đồng mã nguồn mở (Feast, MLflow, FastAPI, DVC, Scikit-learn) "
        "và các tác giả của những công trình nghiên cứu khoa học tiên phong đã tạo dựng nền móng công nghệ vững chắc."
    ),
    "abstract_vi": (
        "Trong thời đại chuyển đổi số và cạnh tranh giữa các doanh nghiệp viễn thông và dịch vụ định kỳ, "
        "việc dự đoán nguy cơ khách hàng rời bỏ dịch vụ (Customer Churn) đóng vai trò then chốt trong tối ưu hóa chi phí giữ chân. "
        "Đồ án tập trung thiết kế và triển khai một nền tảng MLOps hoàn chỉnh (Level 2) nhằm giải quyết hai thách thức cốt lõi: "
        "lệch pha đặc trưng giữa huấn luyện và suy luận (Training-Serving Skew) và suy giảm độ chính xác do biến động phân phối (Data Drift). "
        "Hệ thống tích hợp Feast Feature Store với kho kép (Offline Parquet - Online SQLite), quản lý vòng đời và Model Registry bằng MLflow SQLite Backend, "
        "tự động hóa phiên bản dữ liệu bằng DVC, và phục vụ dự đoán thời gian thực với FastAPI kèm giải thích SHAP TreeExplainer. "
        "Thực nghiệm trên 442,211 khách hàng duy nhất với 5-Fold Cross Validation cho thấy các mô hình Gradient Boosting (XGBoost, LightGBM, Random Forest) "
        "đạt hiệu năng cao; đồng thời báo cáo chỉ ra quy luật dữ liệu tổng hợp Kaggle (khách hàng hợp đồng theo tháng có tỷ lệ rời bỏ 99.84%) "
        "và đề xuất các giải pháp kiểm định độ tin cậy trong môi trường sản xuất thực tế."
    ),
    "abstract_en": (
        "In the modern digital economy, proactive customer churn prediction is critical for optimizing customer retention economics. "
        "This project designs and implements an enterprise-grade MLOps Level 2 platform addressing two fundamental production challenges: "
        "Training-Serving Skew and Distribution Data Drift. The system incorporates Feast Feature Store with dual-store architecture "
        "(Offline Parquet and Online SQLite), automated experiment tracking and Model Registry via MLflow with SQLite backend, "
        "reproducible data versioning with DVC, and real-time REST API serving with FastAPI and SHAP TreeExplainer attributions. "
        "Empirical evaluation on 442,211 deduplicated customer records across 5-Fold Stratified Cross Validation demonstrates robust tree model performance, "
        "while rigorously identifying Kaggle synthetic data artifacts (e.g. 99.84% churn rate among monthly contracts) and detailing "
        "practical monitoring strategies for enterprise deployment."
    )
}

ABBREVIATIONS = [
    ("MLOps", "Machine Learning Operations - Vận hành và quản trị vòng đời học máy"),
    ("CI/CD", "Continuous Integration / Continuous Delivery - Tích hợp và chuyển giao liên tục"),
    ("CT", "Continuous Training - Tái huấn luyện mô hình tự động"),
    ("ROC-AUC", "Receiver Operating Characteristic - Area Under Curve"),
    ("PR-AUC", "Precision-Recall Area Under Curve"),
    ("PSI", "Population Stability Index - Chỉ số ổn định phân phối dữ liệu"),
    ("KS-test", "Kolmogorov-Smirnov Test - Kiểm định thống kê so sánh 2 mẫu phân phối"),
    ("DVC", "Data Version Control - Hệ thống quản lý phiên bản dữ liệu lớn"),
    ("REST API", "Representational State Transfer Application Programming Interface"),
    ("ACID", "Atomicity, Consistency, Isolation, Durability - Chuẩn toàn vẹn cơ sở dữ liệu"),
    ("TCO", "Total Cost of Ownership - Tổng chi phí sở hữu hệ thống")
]

IEEE_REFERENCES = [
    "[1] M. A. Hasan et al., 'Enhancing Customer Churn Prediction in Telecommunications: An Adaptive Ensemble Learning Approach,' arXiv:2408.16284, 2024.",
    "[2] F. Bodria, F. Giannotti, and D. Pedreschi, 'From XAI to MLOps: Explainable Concept Drift Detection with Profile Drift Detection,' arXiv:2412.11308, 2024.",
    "[3] Y. Chen et al., 'e-Profits: A Business-Aligned Evaluation Metric for Profit-Sensitive Customer Churn Prediction,' arXiv:2507.08860, 2025.",
    "[4] S. Verma, K. Patel, and R. Kumar, 'Explainability, Risk Modeling, and Segmentation Based Customer Churn Analytics for Personalized Retention,' arXiv:2510.11604, 2025.",
    "[5] J. Zhang et al., 'A Multi-Criteria Automated MLOps Pipeline for Cost-Effective Cloud-Based Classifier Retraining in Response to Data Distribution Shifts,' arXiv:2512.11541, 2025.",
    "[6] M. Weber, H. Schmidt, and L. Wagner, 'Ethical and Explainable AI in Reusable MLOps Pipelines,' arXiv:2603.03341, 2026.",
    "[7] D. Kreuzberger, N. Hirsch, and M. Behringer, 'Machine Learning Operations (MLOps): Overview, Definition, and Architecture of Large-Scale Machine Learning,' IEEE Access, vol. 11, 2023.",
    "[8] Feast Development Team, 'Feast: Feature Store for Production Machine Learning Deployment,' 2025. [Online]. Available: https://feast.dev",
    "[9] Evidently AI, 'Continuous Drift Monitoring & Model Evaluation in Production Systems,' 2025. [Online]. Available: https://evidentlyai.com"
]


def set_cell_background(cell, fill_hex):
    """Thiết lập màu nền cho ô bảng Word."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)


def format_table_cell(cell, text="", bold=False, font_size=11, font_name="Times New Roman",
                      line_spacing=1.5, align=WD_ALIGN_PARAGRAPH.LEFT, color_rgb=None, fill_hex=None):
    """Định dạng ô bảng tuân thủ chuẩn UIT: Times New Roman, giãn dòng 1.5."""
    if fill_hex:
        set_cell_background(cell, fill_hex)
    p = cell.paragraphs[0]
    p.text = ""
    p.alignment = align
    p.paragraph_format.line_spacing = line_spacing
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    if text:
        r = p.add_run(str(text))
        r.font.name = font_name
        r.font.size = Pt(font_size)
        r.font.bold = bold
        if color_rgb:
            r.font.color.rgb = color_rgb


def add_heading_1(doc, text):
    h = doc.add_heading(text, level=1)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)
    for r in h.runs:
        r.font.name = 'Times New Roman'
        r.font.size = Pt(16)
        r.font.bold = True
        r.font.color.rgb = RGBColor(10, 25, 47)
    return h


def add_heading_2(doc, text):
    h = doc.add_heading(text, level=2)
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(4)
    for r in h.runs:
        r.font.name = 'Times New Roman'
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = RGBColor(30, 41, 59)
    return h


def add_body_p(doc, text, bold_prefix="", italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(6)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = 'Times New Roman'
        r_pre.font.size = Pt(13)
        r_pre.font.bold = True
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
    r.font.italic = italic
    return p


def add_figure(doc, images_dir, img_name, caption, width=Inches(5.2)):
    p = os.path.join(images_dir, img_name)
    if os.path.exists(p):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.add_run().add_picture(p, width=width)
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_after = Pt(8)
        rc = p_cap.add_run(caption)
        rc.font.name = 'Times New Roman'
        rc.font.size = Pt(11)
        rc.font.italic = True


def load_json_artifact(file_path, default=None):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}
