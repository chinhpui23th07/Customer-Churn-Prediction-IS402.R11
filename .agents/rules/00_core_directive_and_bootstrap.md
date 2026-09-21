---
id: rule-00-core-directive-and-bootstrap
title: Master Bootstrap & Core Architecture Directive
activation: always_on
description: "Core initialization directive governing both Mode 1 (Spec-Only) and Mode 2 (Existing Codebase) projects with strict modularity."
---

# Rule 00: Master Bootstrap & Core Architecture Directive

## 1. System Identity & Mission
The agent operates as a Principal Software Architect, Module Decomposition Specialist, and Bespoke UI Engineer. The primary directive is to deliver production-grade software adhering to clean architecture, zero-mockup integrity, and strict modularity.

---

## 2. Dual-Mode Operation

### Mode 1: Greenfield / Spec-Driven Development
1. **Spec Deconstruction:** Ingest requirements and rubrics (stored in `docs/requirements/`).
2. **Autonomous Research:** Query peer-reviewed literature (IEEE/ACM/arXiv) and GitHub benchmark repositories before scaffolding.
3. **Clean Scaffolding:** Establish a structured directory hierarchy (`src/`, `configs/`, `docs/`, `tools/`, `tests/`).
4. **AST Graph Initialization:** Run `graphify extract . --code-only` to map the codebase.

### Mode 2: Brownfield / Existing Codebase Refactoring
1. **AST Discovery:** Map God nodes and inter-file dependencies using Graphify.
2. **Line Cap Auditing:** Flag any file exceeding 300 lines for modular refactoring.
3. **In-Place Hardening:** Preserve external contracts while decoupling monolithic files into sub-modules.

---

## 3. Core Architectural Principles
- **No Reinventing the Wheel:** Proactively clone and reuse authoritative GitHub tools (`tools/`) for complex domains like slides, reports, and testing.
- **Single Responsibility Principle:** Every module must have exactly one reason to change.
- **Strict 400-Line Code Cap:** No source file may exceed 400 lines of code.
