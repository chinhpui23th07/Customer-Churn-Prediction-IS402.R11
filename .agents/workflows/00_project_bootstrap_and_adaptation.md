---
id: workflow-00-project-bootstrap-and-adaptation
title: Standard Operating Procedure (SOP) for Project Initialization & Scaffolding
---

# SOP 00: Project Initialization & Adaptation Procedure

## 1. Purpose
Defines the step-by-step procedure for initializing both Greenfield (spec-driven) and Brownfield (existing codebase) projects.

---

## 2. Step-by-Step Procedure

```text
[Step 1: Requirement Ingestion]
  ├── Ingest spec files from docs/requirements/
  └── Extract architectural deliverables and evaluation rubrics
       │
       ▼
[Step 2: Autonomous Research & Benchmarking]
  ├── Search & download academic PDFs into docs/research/papers/
  ├── Query GitHub MCP and shallow clone benchmark repos into docs/research/repos/
  └── Look up official SDK syntax via Context7
       │
       ▼
[Step 3: Open-Source Tool Setup]
  ├── Clone presentation tooling (tools/reveal.js)
  └── Clone document templating engines (tools/docxtpl)
       │
       ▼
[Step 4: Clean Layered Scaffolding]
  ├── src/ (config, data, features, models, monitoring, api, web)
  ├── tests/ (unit, integration, and drift tests)
  └── configs/ (cloud architecture and settings)
       │
       ▼
[Step 5: Initial AST Knowledge Graph Generation]
  └── cmd /c "python -m graphify.cli extract . --code-only"
```
