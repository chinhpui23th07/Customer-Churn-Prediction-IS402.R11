---
id: rule-05-anti-mockup-and-adversarial-gates
title: Anti-Mockup & Adversarial Quality Assurance Protocol
activation: always_on
description: "Enforces 100% genuine data, real API execution, real database queries, and mandatory pre-handover verification gates."
---

# Rule 05: Anti-Mockup & Adversarial Quality Assurance Protocol

## 1. Absolute Engineering Truth
- **Strict Anti-Mockup Mandate:** Mockups, fake responses, synthetic placeholders, and simulated delays are strictly prohibited in production code paths.
- All machine learning pipelines must train on authentic datasets (e.g. 440,832 Kaggle records).
- Feature stores and databases must persist actual records on disk (SQLite, Parquet, Redis).

---

## 2. Adversarial Scanning
Scan all source directories for forbidden mockup tokens before finalizing any milestone:
```bash
cmd /c "git grep -iE \"TODO: mock|fakeData|dummyData|simulateTx\" -- src/ || echo Clear"
```

---

## 3. Explicit Failure Reporting
Never swallow exceptions with bare `except: pass`. All network timeouts, database errors, and validation failures must surface with original error messages and HTTP status codes.
