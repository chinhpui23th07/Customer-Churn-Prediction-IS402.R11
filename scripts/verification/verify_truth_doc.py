"""Verification script for docs/MASTER_PROJECT_TRUTH.md."""
import re
from pathlib import Path

def main():
    path = Path("docs/MASTER_PROJECT_TRUTH.md")
    if not path.exists():
        print("ERROR: docs/MASTER_PROJECT_TRUTH.md not found!")
        return 1

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # 1. Check Unicode dashes
    bad_chars = {
        '\u2013': 'EN DASH',
        '\u2014': 'EM DASH',
        '\u2015': 'HORIZONTAL BAR',
        '\u2212': 'MINUS SIGN',
    }
    
    found_dashes = []
    for line_idx, line in enumerate(lines, start=1):
        for char, name in bad_chars.items():
            if char in line:
                found_dashes.append((line_idx, name, line.strip()))

    print(f"=== CHECK 1: UNICODE DASHES ===")
    if found_dashes:
        print(f"FAILED: Found {len(found_dashes)} illegal Unicode dash characters:")
        for line_idx, name, line in found_dashes[:10]:
            print(f"  Line {line_idx} ({name}): {line[:80]}")
    else:
        print("PASSED: 0 Unicode em-dashes / en-dashes found (100% standard ASCII hyphen '-')")

    # 2. Check Student PII
    print(f"\n=== CHECK 2: STUDENT PII & ANONYMIZATION ===")
    pii_patterns = [
        r"nguy[eễ]n\s+tr[oọ]ng\s+kh[oô]i",
        r"tr[oọ]ng\s+kh[oô]i",
        r"\b2052\d{4}\b",
        r"\b2152\d{4}\b",
        r"\b2252\d{4}\b",
        r"sinh\s+vi[eê]n\s+th[uự]c\s+hi[eệ]n\s*:\s*(?!\[)",
    ]

    found_pii = []
    for line_idx, line in enumerate(lines, start=1):
        for pat in pii_patterns:
            if re.search(pat, line, re.IGNORECASE):
                found_pii.append((line_idx, line.strip()))

    if found_pii:
        print(f"FAILED: Found {len(found_pii)} lines with potential student PII:")
        for line_idx, line in found_pii[:10]:
            print(f"  Line {line_idx}: {line[:80]}")
    else:
        print("PASSED: No student PII found.")

    # 3. Check Author Anonymization and Supervisor string
    print(f"\n=== CHECK 3: AUTHOR & SUPERVISOR SPECIFICATION ===")
    has_anon_author = any("[Để trống / Tác giả bảo mật]" in line or "[Bảo mật danh tính sinh viên]" in line for line in lines)
    has_supervisor = any("ThS. Hà Lê Hoài Trung" in line for line in lines)
    print(f"Author Anonymized Marker Present: {has_anon_author}")
    print(f"Supervisor 'ThS. Hà Lê Hoài Trung' Present: {has_supervisor}")

    # 4. Summary
    if not found_dashes and not found_pii and has_anon_author and has_supervisor:
        print("\n>>> OVERALL VERDICT: PASSED 100% <<<")
        return 0
    else:
        print("\n>>> OVERALL VERDICT: FAILED <<<")
        return 1

if __name__ == "__main__":
    exit(main())
