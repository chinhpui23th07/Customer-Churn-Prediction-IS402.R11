"""
File Line Count Checker & 400-Line Code Cap Enforcer
Kiem tra gioi han 400 dong cho toan bo cac tep ma nguon trong du an.
Tra ve exit code 0 neu tat ca tep deu <= 400 dong, exit code 1 neu co tep vi pham.
"""
import os
import sys

MAX_LINES = 400
WARN_THRESHOLD = 300

CODE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.sol', 
    '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.php', '.rb',
    '.vue', '.svelte', '.dart', '.kt', '.swift', '.sql'
}

IGNORE_DIRS = {
    'node_modules', '.git', 'dist', 'build', '.agents', 'graphify-out', 
    'temp_tools', 'vendor', '__pycache__', '.venv', 'venv', 'artifacts',
    'coverage', '.next', '.nuxt', 'target', 'bin', 'obj'
}

def count_file_lines(filepath: str) -> int:
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return sum(1 for _ in f)
    except Exception as e:
        print(f"[WARN] Khong the doc file {filepath}: {e}")
        return 0

def scan_directory(root_dir: str = "."):
    violations = []
    warnings = []
    total_files = 0
    
    print(f"\n==================================================================")
    print(f" [LINE CAP AUDIT] Dang kiem tra gioi han 400 dong code tai: {root_dir}")
    print(f"==================================================================")
    
    for root, dirs, files in os.walk(root_dir):
        # Loai bo cac thu muc can bo qua
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in CODE_EXTENSIONS:
                total_files += 1
                full_path = os.path.join(root, file)
                lines = count_file_lines(full_path)
                
                if lines > MAX_LINES:
                    violations.append((full_path, lines))
                elif lines >= WARN_THRESHOLD:
                    warnings.append((full_path, lines))
                    
    print(f"[THONG KE] Da quet tong cong {total_files} tep ma nguon.")
    
    if warnings:
        print(f"\n[CANH BAO - TIEM CAN NGUONG 300-400 DONG]: {len(warnings)} tep")
        for path, count in sorted(warnings, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  * {path} : {count} dong (Nen chuan bi phan ra)")
            
    if violations:
        print(f"\n[VI PHAM - VUOT QUA 400 DONG CODE]: {len(violations)} tep!")
        for path, count in sorted(violations, key=lambda x: x[1], reverse=True):
            print(f"  [X] {path} : {count} dong (> 400 dong - BAT BUOC PHAN RA!)")
        print("\n[FAILED] Yeu cau phan ra cac tep tren truoc khi ban giao!")
        sys.exit(1)
        
    print(f"\n[PASSED] 100% tep ma nguon deu nam trong gioi han <= 400 dong code.")
    print("==================================================================\n")
    sys.exit(0)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_directory(target)
