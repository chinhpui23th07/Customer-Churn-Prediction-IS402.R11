---
id: rule-02-graphify-ast-knowledge-graph
title: Codebase AST Knowledge Graph Synchronization Protocol
activation: always_on
description: "Maintains an up-to-date Abstract Syntax Tree (AST) knowledge graph of all code symbols, imports, and architectural dependencies using Graphify."
---

# Rule 02: Codebase AST Knowledge Graph Synchronization Protocol

## 1. Purpose
To maintain absolute awareness of code relationships, dependencies, and God nodes, the system must synchronize an AST knowledge graph across all engineering phases.

---

## 2. Synchronization Lifecycle

1. **Scaffolding Phase:** Immediately upon creating the codebase scaffolding:
   ```bash
   cmd /c "python -m graphify.cli extract . --code-only"
   ```
2. **Incremental Updates:** Following any file refactoring, module split, or new API addition:
   ```bash
   cmd /c "python -m graphify.cli update ."
   ```
3. **Pre-Handover Verification:** Step 6 of the Mandatory Pre-Handover Adversarial Gate ensures `graphify-out/graph.json` reflects the exact state of the project.

---

## 3. Querying & Navigation
- Check `graphify-out/graph.json` to identify high-degree nodes before modifying shared utilities.
- Isolate components with cyclic dependencies and plan sub-module decouplings.
