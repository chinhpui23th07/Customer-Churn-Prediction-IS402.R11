---
id: rule-04-self-optimization-and-evolution
title: Continuous Self-Optimization & Rule Evolution
activation: always_on
description: "Codifies learnings, developer feedback, and error corrections into persistent rules, skills, and workflows."
---

# Rule 04: Continuous Self-Optimization & Rule Evolution

## 1. Operating Principle
When the user provides corrective feedback or when a systematic failure occurs during development, the agent must not only fix the immediate issue but also evolve the system's persistent governance artifacts.

---

## 2. Evolution Workflow
1. **Identify Pattern:** Pinpoint whether the issue stems from an underspecified rule, an absent skill, or a flawed workflow.
2. **Update Artifacts:**
   - Update or create rules in `.agents/rules/`.
   - Update or create skills in `.agents/skills/`.
   - Update or create workflows in `.agents/workflows/`.
3. **Synchronize Master Governance:** Update `AGENTS.md` to reflect any new invariant or technical standard.
