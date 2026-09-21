---
name: stackoverflow-bug-hunter
description: "Resolves difficult runtime bugs, deprecation warnings, and library incompatibilities by querying exact error signatures against StackOverflow and GitHub Issues."
---

# StackOverflow Bug Hunter Skill

## Mission
Discovers verified community solutions for obscure runtime errors, framework breaking changes, and platform quirks.

---

## 1. Investigation Protocol
1. **Isolate Error Token:** Extract the precise error type, failing module, and version environment.
2. **Query Community Knowledge:**
   - Search: `site:stackoverflow.com "<exact_error_message>"`
   - Search: `site:github.com/<owner>/<repo>/issues "<exact_error_message>"`
3. **Patch Verification:** Apply canonical patches verified by community upvotes and run tests to validate resolution.
