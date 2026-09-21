---
id: rule-08-modular-architecture-and-file-size-limit
title: Modular Decomposition & 400-Line Strict File Cap Protocol
activation: always_on
description: "Enforces single responsibility, strict layered directory structure, and an absolute 400-line hard cap per source file."
---

# Rule 08: Modular Decomposition & 400-Line Strict File Cap Protocol

## 1. The 400-Line Absolute Code Cap (Invariant 02)
- **Hard Limit:** **NO source code file may exceed 400 lines of code.**
- **Threshold Alert:** Once a file reaches 300 lines, the agent must plan sub-module decomposition.
- **Auditing Command:**
  ```bash
  cmd /c "python .agents\skills\modular-code-decomposer\scripts\check_file_lines.py src"
  ```
  Any file exceeding 400 lines will immediately trigger an adversarial verification failure.

---

## 2. Layered Directory Architecture
Maintain clean separation of concerns:
- `src/config/`: Application settings and environment schemas.
- `src/data/`: Ingestion, validation, preprocessing, and benchmark scripts.
- `src/features/`: Feature store definitions, entities, views, and registries.
- `src/models/`: Training pipelines, model evaluation, and artifact tracking.
- `src/monitoring/`: Data drift detectors, statistical tests, and HTML reports.
- `src/api/`: REST API schemas, endpoints, and routers.
- `src/web/`: Presentation UI components and static assets.
- `tools/`: Cloned open-source repositories and compilation tools.
- `tests/`: Automated unit, integration, and drift tests.
