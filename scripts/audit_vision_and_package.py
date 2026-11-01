"""
Công cụ Thẩm định Thị giác (Vision Audit) & Đóng gói Bài nộp Sạch (Clean Packaging).
Môn học: Điện toán đám mây (Cloud Computing) - UIT.
"""
import os
import sys
import argparse
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
SCRATCH_DIR = os.path.join(BASE_DIR, "scratch")
RENDER_DIR = os.path.join(SCRATCH_DIR, "pdf_vision_render")
DEFAULT_PDF = os.path.join(DOCS_DIR, "Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.pdf")
DEFAULT_DOCX = os.path.join(DOCS_DIR, "Bao_Cao_Bai_Tap_Lon_MLOps_Customer_Churn.docx")
DEFAULT_PPTX = os.path.join(DOCS_DIR, "Slide_Thuyet_Trinh_MLOps_Customer_Churn.pptx")


def export_docx_to_pdf_com(docx_path, pdf_path):
    """Xuất PDF từ DOCX sử dụng Microsoft Word Native COM Engine."""
    print(f"[*] Đang chuyển đổi Word DOCX sang PDF qua Word COM Native...")
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(os.path.abspath(docx_path))
        doc.SaveAs(os.path.abspath(pdf_path), FileFormat=17)  # 17 = wdFormatPDF
        doc.Close()
        word.Quit()
        print(f"[OK] Đã xuất PDF thành công: {pdf_path}")
        return True
    except Exception as e:
        print(f"[LỖI] Không thể xuất PDF qua Word COM: {e}")
        return False


def render_pdf_to_images(pdf_path, output_dir=None, dpi=200):
    """Render 100% các trang PDF thành ảnh PNG phân giải cao để kiểm tra Vision."""
    if output_dir is None:
        output_dir = RENDER_DIR
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(pdf_path) or (os.path.exists(DEFAULT_DOCX) and os.path.getmtime(DEFAULT_DOCX) > os.path.getmtime(pdf_path)):
        if os.path.exists(DEFAULT_DOCX):
            print(f"[*] Phát hiện DOCX mới hơn PDF hoặc PDF chưa tồn tại. Đang tự động biên dịch sang PDF qua Word COM...")
            success = export_docx_to_pdf_com(DEFAULT_DOCX, pdf_path)
            if not success and not os.path.exists(pdf_path):
                return []
        else:
            print(f"[LỖI] Không tìm thấy cả DOCX lẫn PDF. Vui lòng chạy generate_docx_report.py trước.")
            return []

    try:
        import fitz  # PyMuPDF
    except ImportError:
        print(f"[LỖI] Thư viện PyMuPDF (fitz) chưa được cài đặt. Chạy: cmd /c pip install pymupdf")
        return []

    print(f"[*] Đang mở tài liệu PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    rendered_files = []

    print(f"[*] Bắt đầu render {total_pages} trang với độ phân giải {dpi} DPI...")
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        img_name = f"page_{i + 1:02d}.png"
        out_path = os.path.join(output_dir, img_name)
        pix.save(out_path)
        rendered_files.append(out_path)
        print(f"    [Trang {i + 1:02d}/{total_pages:02d}] {pix.width}x{pix.height}px -> {img_name}")

    doc.close()
    print(f"[OK] Đã render hoàn tất {len(rendered_files)} trang vào thư mục: {output_dir}")
    print(f"[TIP] Sử dụng công cụ view_file để kiểm tra trực quan từng trang.")
    return rendered_files


def clean_workspace():
    """Tự động dọn dẹp các tệp tạm, __pycache__, .pytest_cache và log hệ thống."""
    import shutil
    print("[*] Đang tự động dọn dẹp các tệp tạm và cache hệ thống...")
    for root, dirs, files in os.walk(BASE_DIR, topdown=False):
        rel_root = os.path.relpath(root, BASE_DIR).replace("\\", "/")
        if rel_root.startswith('.git') or rel_root.startswith('scratch') or rel_root.startswith('docs/research'):
            continue
        for d in dirs:
            if d in ('__pycache__', '.pytest_cache'):
                try:
                    shutil.rmtree(os.path.join(root, d))
                except Exception:
                    pass
        for f in files:
            if f.endswith(('.pyc', '.tmp', '.log', '.bak')):
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
    print("[OK] Đã hoàn tất dọn dẹp cache hệ thống.")


def verify_workspace_cleanliness():
    """Kiểm tra vệ sinh không gian làm việc trước khi bàn giao/đóng gói."""
    print(f"[*] Đang kiểm tra vệ sinh thư mục dự án (Sanitation & Hygiene Check)...")
    forbidden_extensions = ('.pyc', '.tmp', '.log', '.bak')
    forbidden_dirs = ('__pycache__', '.pytest_cache', '.vscode', '.idea')

    violations = []
    for root, dirs, files in os.walk(BASE_DIR):
        # Bỏ qua thư mục .git và scratch khi kiểm tra nội bộ
        rel_root = os.path.relpath(root, BASE_DIR).replace("\\", "/")
        if rel_root.startswith('.git') or rel_root.startswith('scratch') or rel_root.startswith('docs/research') or rel_root.startswith('.pytest_cache'):
            continue

        for d in dirs:
            if d in forbidden_dirs:
                violations.append(f"Thư mục cấm: {os.path.join(rel_root, d)}")

        for f in files:
            if f.endswith(forbidden_extensions) and not rel_root.startswith('scratch'):
                violations.append(f"Tệp rác: {os.path.join(rel_root, f)}")

    if violations:
        print(f"[CẢNH BÁO] Phát hiện {len(violations)} phần tử cần dọn dẹp:")
        for v in violations[:10]:
            print(f"    - {v}")
        if len(violations) > 10:
            print(f"    ... và {len(violations) - 10} phần tử khác.")
        return False
    else:
        print(f"[OK] Workspace hoàn toàn sạch sẽ, không có tệp rác hệ thống.")
        return True


def create_clean_submission_zip(output_zip_path=None):
    """Đóng gói tệp ZIP nộp bài chuẩn UIT: Chỉ chứa mã nguồn sạch và PDF báo cáo."""
    if output_zip_path is None:
        student_id = "23520783"
        output_zip_path = os.path.join(BASE_DIR, f"{student_id}_BTL_Cloud_Computing_MLOps.zip")

    print(f"[*] Bắt đầu đóng gói bài nộp: {output_zip_path}")
    allowed_dirs = ['src', 'configs', 'scripts', 'tests', 'assets', '.github', 'deploy', 'notebooks']
    allowed_files = ['README.md', 'DESIGN.md', 'AGENTS.md', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'dvc.yaml']

    # Danh sách loại trừ nghiêm ngặt
    exclude_extensions = ('.docx', '.pyc', '.tmp', '.log', '.zip', '.bak', '.tar', '.gz')
    exclude_dirs = {'__pycache__', '.pytest_cache', '.vscode', '.idea', 'scratch', 'mlruns', '.dvc_storage', 'graphify-out'}

    packed_count = 0
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 1. Đóng gói tệp PDF báo cáo chính thức và PPTX slide vào docs/
        if os.path.exists(DEFAULT_PDF):
            zipf.write(DEFAULT_PDF, arcname=os.path.join("docs", os.path.basename(DEFAULT_PDF)))
            packed_count += 1
            print(f"    + Đã thêm PDF chính thức: docs/{os.path.basename(DEFAULT_PDF)}")
        else:
            print(f"[CẢNH BÁO] Không tìm thấy {DEFAULT_PDF}! Tệp zip sẽ thiếu báo cáo.")

        if os.path.exists(DEFAULT_PPTX):
            zipf.write(DEFAULT_PPTX, arcname=os.path.join("docs", os.path.basename(DEFAULT_PPTX)))
            packed_count += 1
            print(f"    + Đã thêm Slide PPTX: docs/{os.path.basename(DEFAULT_PPTX)}")

        # 2. Đóng gói các tệp cấu hình gốc
        for root_file in allowed_files:
            file_path = os.path.join(BASE_DIR, root_file)
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=root_file)
                packed_count += 1

        # 3. Đóng gói các thư mục mã nguồn được phép
        for target_dir in allowed_dirs:
            dir_path = os.path.join(BASE_DIR, target_dir)
            if not os.path.exists(dir_path):
                continue
            for root, dirs, files in os.walk(dir_path):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for f in files:
                    if f.endswith(exclude_extensions):
                        continue
                    full_p = os.path.join(root, f)
                    arc_p = os.path.relpath(full_p, BASE_DIR)
                    zipf.write(full_p, arcname=arc_p)
                    packed_count += 1

    file_size_mb = os.path.getsize(output_zip_path) / (1024 * 1024)
    print(f"[OK] Đã đóng gói thành công {packed_count} tệp tin sạch vào: {output_zip_path}")
    print(f"[THÔNG TIN] Dung lượng tệp zip: {file_size_mb:.2f} MB")
    return output_zip_path


def main():
    parser = argparse.ArgumentParser(description="Vision Audit & Clean Submission Packaging Tool")
    parser.add_argument("--export-pdf", action="store_true", help="Biên dịch Word DOCX sang PDF qua Word COM Native")
    parser.add_argument("--render-pdf", nargs="?", const=DEFAULT_PDF, help="Render PDF sang PNG độ phân giải cao")
    parser.add_argument("--dpi", type=int, default=200, help="Độ phân giải khi render PDF (mặc định 200)")
    parser.add_argument("--clean", action="store_true", help="Dọn dẹp tự động tệp rác và __pycache__")
    parser.add_argument("--verify-package", action="store_true", help="Kiểm tra vệ sinh thư mục dự án")
    parser.add_argument("--package", nargs="?", const="DEFAULT", default=None, help="Tạo tệp zip nộp bài sạch chuẩn UIT")

    args = parser.parse_args()

    if not any([args.export_pdf, args.render_pdf, args.clean, args.verify_package, args.package is not None]):
        parser.print_help()
        sys.exit(0)

    if args.clean:
        clean_workspace()

    if args.export_pdf:
        export_docx_to_pdf_com(DEFAULT_DOCX, DEFAULT_PDF)

    if args.render_pdf:
        render_pdf_to_images(args.render_pdf, dpi=args.dpi)

    if args.verify_package:
        verify_workspace_cleanliness()

    if args.package is not None:
        target_zip = None if args.package == "DEFAULT" else args.package
        create_clean_submission_zip(target_zip)


if __name__ == "__main__":
    main()
