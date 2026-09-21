---
id: rule-03-dynamic-skill-orchestration
title: Dynamic Skill Discovery & Orchestration Protocol
activation: always_on
description: "Discovers and dynamically routes specialized capabilities from the Global Skills Hub and local workspace extensions."
---

# Rule 03: Dynamic Skill Discovery & Orchestration Protocol

## 1. Objective
Enable seamless lookup and activation of specialized skills across machine learning, system architecture, database administration, and UI engineering.

---

## 2. Skill Inventory & Hierarchy
1. **Global Skills Hub:** `C:\Users\Nguyen Trong Khoi\.gemini\config\skills\` containing specialized domain skills.
2. **Workspace Custom Skills:** Located in `.agents/skills/` for project-specific operations (e.g. `uit-academic-report-generator`, `modular-code-decomposer`, `github-repo-reuser`).

---

## 3. Invocation Protocol
- Read the relevant `SKILL.md` before executing unfamiliar or complex tasks.
- If a task requires custom tooling (e.g. academic reports, AST extraction, slide compilation), route directly to the designated skill scripts and templates.
