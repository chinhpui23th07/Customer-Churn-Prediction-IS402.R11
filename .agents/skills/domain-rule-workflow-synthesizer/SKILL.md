---
name: domain-rule-workflow-synthesizer
description: "Deconstructs unstructured domain requirements, rubrics, and project specs into actionable engineering rules and standardized operating procedures (SOPs)."
---

# Domain Rule & Workflow Synthesizer Skill

## Mission
Parses unstructured requirements documents (.docx, .xlsx, .pdf) into formalized architectural invariants, rules in `.agents/rules/`, and execution workflows in `.agents/workflows/`.

---

## 1. Operating Procedure
1. **Spec Ingestion:** Parse raw files in `docs/requirements/` to extract constraints, deliverables, and rubric criteria.
2. **Rule Formulation:** Synthesize domain-specific invariants and persist them with YAML frontmatter.
3. **SOP Construction:** Map requirements into deterministic, step-by-step shell workflows.
