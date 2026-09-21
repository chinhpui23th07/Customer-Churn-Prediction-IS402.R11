---
id: workflow-04-pre-handover-adversarial-verification
title: Standard Operating Procedure (SOP) for Pre-Handover Adversarial Quality Verification
---

# SOP 04: Pre-Handover Adversarial Quality Verification Procedure

## 1. Purpose
Enforces a 6-step adversarial gate via terminal executions before any milestone can be handed over or marked complete.

---

## 2. Step-by-Step SOP

```text
[Gate 1: Line Cap Audit]
  └── cmd /c "python .agents\skills\modular-code-decomposer\scripts\check_file_lines.py src && python .agents\skills\modular-code-decomposer\scripts\check_file_lines.py scripts"
       │
       ▼
[Gate 2: Unit & Integration Test Suite]
  └── cmd /c "python -m pytest tests/ -v"
       │
       ▼
[Gate 3: Build Production Deliverables]
  └── cmd /c "python scripts\generate_docx_report.py"
       │
       ▼
[Gate 4: Static Compilation & Type Check]
  └── cmd /c "python -m py_compile src/api/main.py"
       │
       ▼
[Gate 5: Anti-Mockup Codebase Scan]
  └── cmd /c "git grep -iE \"TODO: mock|fakeData|dummyData|simulateTx\" -- src/ || echo Clear"
       │
       ▼
[Gate 6: AST Knowledge Graph Synchronization]
  └── cmd /c "python -m graphify.cli update ."
```
