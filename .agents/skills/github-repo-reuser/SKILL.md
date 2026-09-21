---
name: github-repo-reuser
description: "Identifies, shallow clones, inspects, and reuses reputable open-source GitHub repositories, tools, slide decks, and test suites, preventing reinventing the wheel."
---

# GitHub Repo Reuser Skill

## Mission
To enforce the principle of **standing on the shoulders of giants**. Whenever a specialized technical challenge arises (e.g. presentation slides, Word reports, complex UI animations, MLOps scaffolding, or integration tests), the agent must proactively discover and adapt battle-tested open-source code rather than writing scratch scripts.

---

## 1. Operating Protocol

### Step 1: Discover Repositories via GitHub MCP
Use GitHub MCP tools (`search_repositories` or `get_file_contents`) to locate battle-tested solutions:
```json
{
  "query": "reveal.js presentation slides",
  "perPage": 5
}
```

### Step 2: Shallow Clone to `tools/` or `docs/research/repos/`
Execute shallow clones (`--depth 1`) on Windows:
```bash
cmd /c "git clone --depth 1 https://github.com/<owner>/<repo>.git tools/<tool_name>"
```

### Step 3: Adapt Patterns & Test Suites
- Integrate presentation tooling (e.g. Reveal.js in `tools/reveal.js` or Marp in `docs/slides.marp.md`).
- Integrate document templating (e.g. `docxtpl` in `tools/docxtpl`).
- Adapt production test suites from benchmark repositories into `tests/test_api.py`.
