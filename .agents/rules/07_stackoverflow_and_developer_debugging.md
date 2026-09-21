---
id: rule-07-stackoverflow-and-developer-debugging
title: StackOverflow & Developer Issue Debugging Protocol
activation: always_on
description: "Governs deep root-cause debugging using exact runtime error signatures across StackOverflow and GitHub Issues."
---

# Rule 07: StackOverflow & Developer Issue Debugging Protocol

## 1. Objective
Eliminate trial-and-error guessing when facing complex runtime errors or framework deprecation warnings. Trace root causes directly to verified developer community solutions.

---

## 2. Debugging Procedure
1. **Extract Error Signature:** Capture the exact exception name, module trace, and failing parameter.
2. **Search Verified Solutions:**
   - Search StackOverflow: `site:stackoverflow.com "<exact_error_message>"`
   - Search GitHub Issues: `site:github.com/<owner>/<repo>/issues "<error_signature>"`
3. **Patch Implementation:** Apply canonical community solutions rather than ad-hoc workarounds.
