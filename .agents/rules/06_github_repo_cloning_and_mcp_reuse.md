---
id: rule-06-github-repo-cloning-and-mcp-reuse
title: Mandatory GitHub Open-Source Repository Reuse & Tooling Protocol
activation: always_on
description: "Strict directive mandating the discovery, shallow cloning, and integration of battle-tested GitHub open-source repositories and tools, strictly prohibiting writing complex logic or tools from scratch."
---

# Rule 06: Mandatory GitHub Open-Source Repository Reuse & Tooling Protocol

## 1. The Principle of Standing on the Shoulders of Giants
In modern software engineering, mature open-source solutions already exist for specialized domains such as presentation slide rendering, Word report generation, test suites, and MLOps pipelines.
- **Golden Rule:** **NEVER write from scratch (reinvent the wheel)** when gold-standard GitHub repositories, libraries, or tools exist.
- **Mandatory Action:** The agent must search GitHub repositories via MCP, shallow clone (`--depth 1`) battle-tested tools into `tools/`, and adapt existing patterns into the project.

---

## 2. Standard Open-Source Tooling Mapping

| Task Category | Standard GitHub Solution | Integration Target |
| :--- | :--- | :--- |
| **Slide Presentations** | `hakimel/reveal.js`, `marp-team/marp` | Cloned in `tools/reveal.js` or `docs/slides.marp.md` |
| **Academic Document Reports** | `elapouya/python-docx-template`, `jgm/pandoc` | Cloned in `tools/docxtpl` |
| **Feature Store & MLOps** | `feast-dev/feast`, `mlflow/mlflow` | Configured in `src/features/` & `src/models/` |
| **Data Drift Monitoring** | `evidentlyai/evidently` | Integrated in `src/monitoring/` |
| **Test Suites** | Production suites from benchmark repos | Adopted into `tests/test_api.py` |

---

## 3. Cloning and Integration Standard
- Use shallow clone to minimize download overhead:
  ```bash
  cmd /c "git clone --depth 1 <github_url> tools/<tool_name>"
  ```
- Ground all test suites in the structure of real benchmark repositories (`docs/research/repos/`).
