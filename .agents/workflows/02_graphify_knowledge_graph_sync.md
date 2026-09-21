---
id: workflow-02-graphify-knowledge-graph-sync
title: Standard Operating Procedure (SOP) for AST Knowledge Graph Synchronization
---

# SOP 02: AST Knowledge Graph Synchronization Procedure

## 1. Purpose
Ensures the AST knowledge graph accurately reflects the current structure of code symbols, functions, classes, and inter-file imports.

---

## 2. Step-by-Step SOP

```text
[Step 1: Scaffolding Mapping]
  └── cmd /c "python -m graphify.cli extract . --code-only"
       │
       ▼
[Step 2: Incremental Updates after Refactoring]
  └── cmd /c "python -m graphify.cli update ."
       │
       ▼
[Step 3: Graph Inspection]
  ├── Verify graphify-out/graph.json
  └── Confirm community partitions and modularity indices
```
