---
id: workflow-06-stackoverflow-deep-debugging-sop
title: Standard Operating Procedure (SOP) for Deep Root-Cause Debugging
---

# SOP 06: Deep Root-Cause Debugging Procedure

## 1. Purpose
Defines a deterministic approach to diagnosing and fixing obscure runtime errors, framework breaking changes, and library version mismatches.

---

## 2. Step-by-Step SOP

```text
[Step 1: Extract Exact Error Trace]
  └── Capture exception type, failing callstack, and argument payloads
       │
       ▼
[Step 2: Query Developer Community Knowledge]
  ├── Query StackOverflow: site:stackoverflow.com "<error_message>"
  └── Query GitHub Issues: site:github.com/<repo>/issues "<error_signature>"
       │
       ▼
[Step 3: Root-Cause Remediation]
  ├── Implement official migration or configuration fix
  └── Verify resolution via test suite execution
```
