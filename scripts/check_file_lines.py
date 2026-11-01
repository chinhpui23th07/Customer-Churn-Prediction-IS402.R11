"""File Line Count Checker & 400-Line Code Cap Enforcer.

Enforces Invariant 02 (Hard limit of 400 lines of code per source file).
Returns exit code 0 if all files <= 400 lines, exit code 1 if any violation found.
"""
from __future__ import annotations

import os
import sys

MAX_LINES = 400
WARN_THRESHOLD = 300

CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".sol",
    ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".rb",
    ".vue", ".svelte", ".dart", ".kt", ".swift", ".sql",
}

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", ".agents", "graphify-out",
    "temp_tools", "vendor", "__pycache__", ".venv", "venv", "artifacts",
    "coverage", ".next", ".nuxt", "target", "bin", "obj",
}


def count_file_lines(filepath: str) -> int:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception as exc:
        print(f"[WARN] Cannot read file {filepath}: {exc}")
        return 0


def scan_directory(root_dir: str = ".") -> None:
    violations = []
    warnings = []
    total_files = 0

    print("=" * 70)
    print(f" [LINE CAP AUDIT] Checking 400-line code cap for: {root_dir}")
    print("=" * 70)

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

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

    print(f"[METRICS] Scanned {total_files} source files.")

    if warnings:
        print(f"\n[WARNING - APPROACHING 300-400 LINES]: {len(warnings)} files")
        for path, count in sorted(warnings, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  * {path} : {count} lines")

    if violations:
        print(f"\n[VIOLATION - EXCEEDED 400 LINES]: {len(violations)} files!")
        for path, count in sorted(violations, key=lambda x: x[1], reverse=True):
            print(f"  [X] {path} : {count} lines (> 400 lines!)")
        sys.exit(1)

    print(f"\n[PASSED] 100% source files within <= 400 lines limit.")
    print("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_directory(target)
