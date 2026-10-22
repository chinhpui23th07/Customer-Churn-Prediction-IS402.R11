"""
Module kiểm tra Invariant 02: Giới hạn cứng 400 dòng mã trên mỗi tệp nguồn (src/ và scripts/).
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_lines(directory: str, max_lines: int = 400):
    violations = []
    total_files = 0
    all_files_info = []

    for root, _, files in os.walk(directory):
        if "__pycache__" in root or ".git" in root or ".pytest_cache" in root:
            continue
        for file in files:
            if file.endswith((".py", ".js", ".css", ".html")):
                total_files += 1
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, BASE_DIR).replace("\\", "/")
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        lines = len(f.readlines())
                    all_files_info.append((lines, rel_path))
                    if lines > max_lines:
                        violations.append((lines, rel_path))
                except Exception as e:
                    print(f"[-] Không thể đọc tệp {rel_path}: {e}")

    return total_files, violations, all_files_info

def main():
    print("=" * 80)
    print("KIỂM TRA INVARIANT 02: GIỚI HẠN 400 DÒNG MÃ (src/ & scripts/)")
    print("=" * 80)

    src_dir = os.path.join(BASE_DIR, "src")
    scripts_dir = os.path.join(BASE_DIR, "scripts")

    tot_src, viol_src, info_src = check_lines(src_dir)
    tot_sc, viol_sc, info_sc = check_lines(scripts_dir)

    all_info = sorted(info_src + info_sc, key=lambda x: x[0], reverse=True)

    print(f"Tổng số tệp được kiểm tra: {tot_src + tot_sc} tệp")
    print("\nTop 10 tệp có số dòng lớn nhất:")
    for lines, path in all_info[:10]:
        status = "⚠️ CẢNH BÁO > 350 DÒNG" if lines > 350 else "✅ ĐẠT CHUẨN"
        print(f"  [{lines:3d} dòng] {path:<45} {status}")

    total_violations = len(viol_src) + len(viol_sc)
    if total_violations > 0:
        print(f"\n❌ VI PHẠM INVARIANT 02: Có {total_violations} tệp vượt quá 400 dòng:")
        for lines, path in viol_src + viol_sc:
            print(f"  * {path}: {lines} dòng (> 400 dòng!)")
        sys.exit(1)
    else:
        print(f"\n✅ 100% TỆP TUÂN THỦ INVARIANT 02 (0 tệp vượt quá 400 dòng)!")

if __name__ == "__main__":
    main()
