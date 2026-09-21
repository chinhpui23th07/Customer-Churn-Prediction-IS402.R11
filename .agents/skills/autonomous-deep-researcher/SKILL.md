---
name: autonomous-deep-researcher
description: "Autonomous technical research: queries scientific literature (IEEE, ACM, arXiv), benchmarks GitHub repositories via GitHub MCP, and looks up official API specs via Context7."
---

# Autonomous Deep Researcher Skill

This skill guides the agent in conducting in-depth technical research before implementing software architectures or machine learning pipelines.

## 1. When to Activate This Skill
- Initializing a new project and establishing architecture baselines.
- Encountering unfamiliar frameworks, algorithms, or protocol specifications (RFC, IEEE, NIST).
- Discovering gold-standard open-source repositories to adopt proven design patterns.
- Downloading peer-reviewed papers to support academic reporting.

---

## 2. 4-Step Research Execution

### Step 1: Scientific Literature Acquisition
- Identify peer-reviewed publications and download official full-text PDFs into `docs/research/papers/`.
- Extract verified algorithms, metric baselines (ROC-AUC, F1, PR-AUC), and data drift thresholds (KS-test, PSI).

### Step 2: GitHub Repository Benchmarking
- Query GitHub MCP (`search_repositories`) for active, production-grade repositories:
  ```json
  { "query": "<domain_topic> stars:>50 best practices" }
  ```
- Shallow clone top reference repositories into `docs/research/repos/<repo_name>/`.
- Analyze folder structures, data pipelines, and production test suites.

### Step 3: Authoritative API Verification (Context7)
- Use `resolve-library-id` and `query-docs` to retrieve exact method signatures and prevent deprecation errors.

### Step 4: Persistent Documentation
- Synthesize all findings into structured markdown documents in `docs/research/` (`academic_papers_review.md`, `github_benchmark_repos.md`, `context7_api_patterns.md`).
