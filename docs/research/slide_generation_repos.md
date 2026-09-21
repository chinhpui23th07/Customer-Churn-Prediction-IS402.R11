# Open-Source Slide Generation Repositories: Architectural Survey & Benchmarks

> **Objective:** Survey, benchmark, and evaluate gold-standard open-source GitHub repositories for automated presentation slide generation.  
> **Compliance:** Rule 01 (Autonomous Research Protocol) & Rule 06 (Mandatory Open-Source & GitHub Reuse).

---

## 1. Executive Summary
Writing presentation slides from scratch or hardcoding shapes in ad-hoc scripts is brittle and difficult to maintain. The open-source community has developed mature presentation engines categorized into:
1. **HTML/CSS/JS Engines (Web-Native):** High fidelity, interactive animations, cross-platform (`reveal.js`).
2. **Markdown-Driven Engines (Developer-First):** Declarative markdown syntax, zero visual boilerplate (`marp`, `slidev`).
3. **Programmatic Office OpenXML Engines:** Direct binary output for Microsoft PowerPoint (`python-pptx`, `pptxgenjs`).

---

## 2. GitHub Benchmark Repositories Evaluated

### ⭐️ Repo 1: `hakimel/reveal.js` (The HTML Presentation Framework)
- **Repository:** `https://github.com/hakimel/reveal.js` (Stars: 67k+)
- **Architecture:** Web-based presentation runtime built on modern CSS Flexbox/Grid, CSS3 3D transforms, and vanilla JavaScript.
- **Key Strengths:**
  - Rich speaker view with notes, timers, and upcoming slide previews.
  - Interactive charts, syntax highlighting, and live DOM rendering.
  - Full keyboard control (`Arrows`, `Space`, `ESC` slide overview).
  - Can be hosted directly on static web servers or opened locally via `index.html`.
- **Project Adoption:**
  - Shallow cloned directly into [`tools/reveal.js/`](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/tools/reveal.js).
  - Configured complete 14-slide interactive presentation in [`tools/reveal.js/index.html`](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/tools/reveal.js/index.html).

---

### ⭐️ Repo 2: `marp-team/marp` (Markdown Presentation Ecosystem)
- **Repository:** `https://github.com/marp-team/marp` (Stars: 6k+)
- **Architecture:** Declarative Markdown-to-Slide pipeline parsing custom directives (`marp: true`, `theme: default`, `paginate: true`) and generating responsive HTML5 / PDF / PPTX decks.
- **Key Strengths:**
  - Zero presentation drift: Slides are version-controlled text files.
  - Support for mathematical formulas ($\LaTeX$), scoped CSS overrides, and custom themes.
- **Project Adoption:**
  - Authored standard 16-slide Marp deck in [`docs/slides.marp.md`](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/docs/slides.marp.md).

---

### ⭐️ Repo 3: `slidevjs/slidev` (Presentation Slides for Developers)
- **Repository:** `https://github.com/slidevjs/slidev` (Stars: 32k+)
- **Architecture:** Vue 3 and Vite-powered slide generator with UnoCSS and interactive Vue components.
- **Key Strengths:**
  - Live interactive code editing during presentations.
  - Recording and camera overlay mode.
- **Evaluation:** Ideal for frontend presentations; heavier build footprint than Reveal.js.

---

### ⭐️ Repo 4: `scanny/python-pptx` (Python PowerPoint Library)
- **Repository:** `https://github.com/scanny/python-pptx` (Stars: 6.5k+)
- **Architecture:** Low-level ECMA-376 OpenXML library for manipulating `.pptx` archives in pure Python.
- **Key Strengths:**
  - Native binary `.pptx` generation without requiring Microsoft Office.
  - Pixel-perfect shapes, tables, and typography hierarchy.
- **Project Adoption:**
  - Powers automated presentation generation in `scripts/generate_pptx_slides.py`.

---

## 3. Comparative Technical Benchmark Matrix

| Feature | `reveal.js` | `marp` | `slidev` | `python-pptx` |
| :--- | :---: | :---: | :---: | :---: |
| **Output Formats** | HTML, PDF | HTML, PDF, PPTX | HTML, PDF, PNG | Native PPTX |
| **Interactivity** | Extremely High | Medium | Very High | Static |
| **Version Control** | Text/HTML | Pure Markdown | Markdown + Vue | Python Script |
| **Offline Viewing** | Any Browser | Any Browser / PDF | Node Server | MS PowerPoint |
| **Adoption in ChurnGuard** | **Cloned in `tools/reveal.js`** | **Authored in `docs/slides.marp.md`** | Referenced | **Exported as `docs/*.pptx`** |
