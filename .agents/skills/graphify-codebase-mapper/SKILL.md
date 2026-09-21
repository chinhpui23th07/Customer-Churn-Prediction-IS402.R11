---
name: graphify-codebase-mapper
description: "Extracts and synchronizes Abstract Syntax Tree (AST) knowledge graphs of codebases using Graphify CLI, enabling God-node identification and dependency analysis."
---

# Graphify Codebase Mapper Skill

## Mission
Maintains a live topological map of the codebase's symbols, functions, classes, and module dependencies in `graphify-out/`.

---

## 1. Commands
- **Full Code Extraction:**
  ```bash
  cmd /c "python -m graphify.cli extract . --code-only"
  ```
- **Incremental Graph Update:**
  ```bash
  cmd /c "python -m graphify.cli update ."
  ```
- Inspect `graphify-out/graph.json` to analyze graph density, modularity scores, and dependency cycles.
