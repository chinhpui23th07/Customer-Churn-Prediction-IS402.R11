---
id: workflow-07-modular-decomposition-and-refactoring-sop
title: Standard Operating Procedure (SOP) for Modular Decomposition & Refactoring
---

# SOP 07: Modular Decomposition & Refactoring Procedure

## 1. Purpose
Governs the proactive refactoring of growing source files to strictly maintain the 400-line hard cap.

---

## 2. Step-by-Step SOP

```text
[Step 1: Detect File Growth]
  └── Run check_file_lines.py; flag any file exceeding 300 lines
       │
       ▼
[Step 2: Decouple Sub-Modules]
  ├── Move Pydantic/dataclass schemas to schemas.py
  ├── Move transformation or helper math logic to utils.py
  └── Move heavy text/metadata dictionaries to content modules
       │
       ▼
[Step 3: Verification & Re-Audit]
  ├── Verify all files are <= 400 lines
  ├── Run tests to ensure zero regressions
  └── Run graphify update . to sync AST knowledge graph
```
