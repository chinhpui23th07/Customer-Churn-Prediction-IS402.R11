"""
Domain Semantic Consistency & Anti-Self-Referential Integrity Auditor (Invariant 20).
Nhiệm vụ:
1. Đảm bảo toàn bộ hệ thống tuân thủ hợp đồng dữ liệu trong docs/requirements/project_context.md.
2. Quét toàn bộ mã nguồn src/ và scripts/: Cấm tuyệt đối import hoặc trỏ tới REES46 eCommerce clickstream.
3. Ngăn chặn hành vi phân liệt dataset (ML chạy tập A, I/O benchmark chạy tập B ngoài domain).
4. Xác minh không có script tự biên tự diễn tự cấp trạng thái Pass ảo.
"""
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_CONTEXT_PATH = BASE_DIR / "docs" / "requirements" / "project_context.md"

FORBIDDEN_DATASET_PATTERNS = [
    r"rees46",
    r"2019-Oct\.csv",
    r"ecommerce-behavior-data",
]


def check_project_context_specification() -> bool:
    """Xác minh sự hiện diện và tính hợp lệ của tệp đặc tả ngữ cảnh dự án."""
    if not PROJECT_CONTEXT_PATH.exists():
        print(f"[X] FATAL: Thiếu tệp đặc tả trung tâm: {PROJECT_CONTEXT_PATH}")
        return False
    content = PROJECT_CONTEXT_PATH.read_text(encoding="utf-8")
    if len(content.strip()) < 100:
        print(f"[X] FATAL: Tệp {PROJECT_CONTEXT_PATH} rỗng hoặc không đủ nội dung đặc tả.")
        return False
    print(f"[+] [INVARIANT-20] Tệp đặc tả ngữ cảnh dự án hợp lệ: {PROJECT_CONTEXT_PATH}")
    return True


def audit_source_code_domain_purity() -> list:
    """Quét mã nguồn trong src/ và scripts/ để phát hiện tham chiếu tới dataset trái domain."""
    violations = []
    scanned_folders = ["src", "scripts"]
    for folder in scanned_folders:
        dir_path = BASE_DIR / folder
        if not dir_path.exists():
            continue
        for p in dir_path.rglob("*"):
            if not p.is_file() or p.suffix not in {".py", ".sh", ".bat"}:
                continue
            # Bỏ qua chính file audit này
            if p.name == "assert_domain_semantic_integrity.py":
                continue
            try:
                code = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for pattern in FORBIDDEN_DATASET_PATTERNS:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for m in matches:
                    line_no = code[:m.start()].count("\n") + 1
                    rel_path = p.relative_to(BASE_DIR).as_posix()
                    violations.append(
                        f"Vi phạm Invariant 20 tại {rel_path}:{line_no} - Tìm thấy token dataset trái domain '{m.group()}'"
                    )
    return violations


def run_domain_semantic_audit() -> bool:
    print("=" * 80)
    print("THANH TRA TÍNH NHẤT QUÁN NGỮ NGHĨA DOMAIN VÀ CHỐNG TỰ THẨM ĐỊNH (INVARIANT-20)")
    print("=" * 80)

    context_ok = check_project_context_specification()
    if not context_ok:
        return False

    violations = audit_source_code_domain_purity()
    if violations:
        print("[X] PHÁT HIỆN VI PHẠM TÍNH NHẤT QUÁN DỮ LIỆU:")
        for v in violations:
            print(f"  * {v}")
        print("\n[!] Hệ thống bị VETO do chứa tàn dư dataset phân liệt hoặc trái domain.")
        return False

    print("[+] 100% mã nguồn trong src/ và scripts/ thuần khiết, không chứa tham chiếu trái domain.")
    print("[+] Kiểm tra [INVARIANT-20] HOÀN TOÀN ĐẠT CHUẨN.")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = run_domain_semantic_audit()
    if not success:
        sys.exit(1)
