#!/usr/bin/env python
"""
FINAL COMPREHENSIVE AUDIT & DUAL-TRACK RUBRIC VERIFICATION (R01..R19).
Consumes AcademicIntegrityAuditor as the single source of truth for the
19 official criteria (10.00 total) and executes dynamic engineering gates.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT_VERIF_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_VERIF_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_VERIF_DIR)

from integrity_rubric_checker import AcademicIntegrityAuditor


def _run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def check_engineering_gates() -> Dict[str, Any]:
    """Run dynamic line-cap, DVC status, semantic integrity, and pytest gates."""
    print("\n[ENGINEERING GATES & PREREQUISITES]")
    print("-" * 82)

    line_results: Dict[str, bool] = {}
    for target in ("src", "scripts", "tests"):
        res_line = _run_cmd([
            sys.executable,
            ".agents/skills/modular-code-decomposer/scripts/check_file_lines.py",
            target,
        ])
        ok = (res_line.returncode == 0) and ("[PASSED]" in res_line.stdout)
        line_results[target] = ok
        print(f"  [{'PASSED' if ok else 'FAILED'}] 400-line cap ({target}/)")
    line_passed = all(line_results.values())

    dvc_bin = shutil.which("dvc")
    dvc_cmd = [dvc_bin, "status"] if dvc_bin else [sys.executable, "-m", "dvc", "status"]
    res_dvc = _run_cmd(dvc_cmd)
    dvc_passed = res_dvc.returncode == 0
    print(f"  [{'PASSED' if dvc_passed else 'FAILED'}] dvc status (exit={res_dvc.returncode})")

    res_dom = _run_cmd([sys.executable, "scripts/verification/assert_domain_semantic_integrity.py"])
    domain_passed = res_dom.returncode == 0
    print(f"  [{'PASSED' if domain_passed else 'FAILED'}] Semantic single-domain integrity (INVARIANT-20)")

    res_test = _run_cmd([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"])
    out_text = f"{res_test.stdout}\n{res_test.stderr}"
    m_pass = re.search(r"(\d+)\s+passed", out_text)
    m_skip = re.search(r"(\d+)\s+skipped", out_text)
    m_fail = re.search(r"(\d+)\s+failed", out_text)
    passed_cnt = int(m_pass.group(1)) if m_pass else 0
    skipped_cnt = int(m_skip.group(1)) if m_skip else 0
    failed_cnt = int(m_fail.group(1)) if m_fail else 0
    test_passed = (res_test.returncode == 0) and (passed_cnt > 0) and (failed_cnt == 0)
    print(
        f"  [{'PASSED' if test_passed else 'FAILED'}] pytest tests/: "
        f"{passed_cnt} passed, {skipped_cnt} skipped, {failed_cnt} failed"
    )

    return {
        "line_cap_400": {"passed": line_passed, "targets": line_results},
        "dvc_status": {"passed": dvc_passed, "exit_code": res_dvc.returncode},
        "domain_semantic_integrity": {"passed": domain_passed},
        "pytest_suite": {
            "passed": test_passed,
            "passed_count": passed_cnt,
            "skipped_count": skipped_cnt,
            "failed_count": failed_cnt,
        },
        "all_passed": line_passed and dvc_passed and domain_passed and test_passed,
    }


def main() -> int:
    verdict = AcademicIntegrityAuditor().evaluate_all()
    rows = verdict["official_rubric_r01_r19"]

    local_rubric_scores: Dict[str, float] = {}
    target_cloud_scores: Dict[str, float] = {}
    cloud_penalties: Dict[str, str] = {}

    current_group = None
    for r in rows:
        if r["group"] != current_group:
            current_group = r["group"]
            print(f"\n[{current_group.upper()}]")
            print("-" * 82)
        rid = r["id"]
        local_rubric_scores[rid] = r["local_score"]
        target_cloud_scores[rid] = r["cloud_readiness_score"]
        if r["local_score"] < r["cloud_readiness_score"]:
            cloud_penalties[rid] = r["deduction_reason"]
        tag = "[+]" if r["local_score"] == r["cloud_readiness_score"] else "[!]"
        print(f"  {tag} {rid} {r['name']}: {r['local_score']:.2f}/{r['max_points']:.2f}d | {r['evidence']}")

    gates = check_engineering_gates()

    tot_local = verdict["local_real_score"]
    tot_cloud = verdict["target_cloud_score"]
    tot_penalties = verdict["total_penalized_points"]

    print("\n" + "=" * 82)
    print("       DUAL-TRACK ACADEMIC INTEGRITY SCORE: LOCAL VS CLOUD TARGET")
    print("=" * 82)
    print(f"  - LOCAL VERIFIED SCORE (Current Disk Evidence) : {tot_local:.2f} / 10.00")
    print(f"  - DEDUCTIONS (Missing Live Cloud / Full >=4GB)  : -{tot_penalties:.2f}")
    print(f"  - CLOUD TARGET SCORE (After Azure Deployment)  : {tot_cloud:.2f} / 10.00")
    print("=" * 82)

    summary_file = os.path.join(BASE_DIR, "data", "processed", "final_check_results.json")
    os.makedirs(os.path.dirname(summary_file), exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "audit_standard": verdict["audit_standard"],
                "evaluator_mode": "Strict Academic Integrity (Dual-Track Local vs Cloud)",
                "local_real_score": tot_local,
                "target_cloud_score": tot_cloud,
                "total_penalized_points": tot_penalties,
                "max_score": 10.0,
                "local_rubric_scores": local_rubric_scores,
                "target_cloud_scores": target_cloud_scores,
                "cloud_penalties_breakdown": cloud_penalties,
                "official_rubric_r01_r19": rows,
                "engineering_gates_passed": gates["all_passed"],
                "engineering_gates": gates,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"[+] Saved transparent audit verdict: {summary_file}")
    return 0 if gates["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
