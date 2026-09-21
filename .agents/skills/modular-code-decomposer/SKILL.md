---
name: modular-code-decomposer
description: "Decomposes monolithic codebases into decoupled, single-responsibility modules and audits the strict 400-line hard cap per source file."
---

# Modular Code Decomposer Skill

This skill monitors codebase complexity and enforces modular decomposition, ensuring no source file exceeds 400 lines of code.

## 1. Activation Triggers
- Scaffolding new directory structures with layered separation of concerns.
- Identifying any source file approaching 300 lines of code.
- Running pre-handover adversarial quality gates.

---

## 2. 3-Step Decomposition Procedure

### Step 1: Scan All Source Files
Execute the line cap audit:
```bash
cmd /c "python .agents\skills\modular-code-decomposer\scripts\check_file_lines.py src"
```

### Step 2: Extraction Patterns
- **Extract Data Validation:** Move validation schemas to `schemas/` or `validators/`.
- **Extract Business Rules:** Separate mathematical and transformation rules into dedicated service modules.
- **Extract UI Elements:** Break complex pages into presentation components under 200 lines.

### Step 3: Verify and Sync AST
- Re-run `check_file_lines.py` to confirm 100% compliance.
- Run `graphify update .` to update the AST knowledge graph.
