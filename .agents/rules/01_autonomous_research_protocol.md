---
id: rule-01-autonomous-research-protocol
title: Autonomous Research & Tooling Protocol (Scientific Papers, GitHub MCP, Context7)
activation: always_on
description: "Mandatory protocol for autonomous research: query and download academic literature, discover and benchmark GitHub repositories via MCP, and look up authoritative APIs via Context7."
---

# Rule 01: Autonomous Research & Tooling Protocol

## 1. Core Mandate
Never make architectural decisions or select libraries without prior empirical and academic grounding. When presented with a task or problem domain:
1. **Academic Literature:** Search peer-reviewed publications (IEEE, ACM, arXiv) and download full-text PDFs into `docs/research/papers/`.
2. **GitHub Benchmark Repositories:** Search open-source repositories via GitHub MCP (`search_repositories`), inspect core architectures, and shallow clone benchmark projects into `docs/research/repos/`.
3. **Authoritative API Verification:** Query Context7 (`resolve-library-id`, `query-docs`) to ensure compliance with the latest framework APIs.

---

## 2. Research Execution Standards

### 2.1. Academic Paper Acquisition & Review
- Identify foundational papers defining the state-of-the-art algorithms, metric baselines, and data drift detection techniques.
- Download actual research papers directly into `docs/research/papers/`.
- Summarize key findings in `docs/research/academic_papers_review.md`.

### 2.2. GitHub Repository Benchmarking
- Query GitHub MCP for active, production-grade repositories:
  ```json
  { "query": "<domain_topic> stars:>50 best practices" }
  ```
- Shallow clone top repositories into `docs/research/repos/<repo_name>/`.
- Compile technical benchmark matrices comparing feature stores, tracking, and drift detection in `docs/research/github_benchmark_repos.md`.

### 2.3. Context7 API Verification
- Query Context7 for modern SDK patterns (e.g. Feast v0.40+ entity definitions, MLflow SQLite backend URIs, Pydantic v2 schemas).
- Record verified code snippets in `docs/research/context7_api_patterns.md`.
