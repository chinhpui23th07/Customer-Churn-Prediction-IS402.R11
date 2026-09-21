# Open-Source DOCX & Academic Report Generation Repositories: Technical Survey

> **Objective:** Survey, benchmark, and evaluate gold-standard open-source GitHub repositories for automated Microsoft Word (`.docx`) document synthesis and academic thesis reporting.  
> **Compliance:** Rule 01 (Autonomous Research Protocol) & Rule 06 (Mandatory Open-Source & GitHub Reuse).

---

## 1. Executive Summary
Generating complex academic reports or enterprise documentation manually in Word is prone to human error and formatting drift. The open-source community provides two primary architectural paradigms:
1. **Template-Driven Engines (Jinja2 Interpolation):** Define a base Word document with pre-styled headers, margins, and placeholders, then inject structured data (`docxtpl`).
2. **Procedural Document Builders (OpenXML DOM Manipulation):** Build paragraphs, runs, tables, and XML properties programmatically (`python-docx`).
3. **Markup Converters (Markdown to Word):** Write in GFM/LaTeX and compile to Word via reference templates (`pandoc`).

---

## 2. GitHub Benchmark Repositories Evaluated

### ⭐️ Repo 1: `elapouya/python-docx-template` (docxtpl)
- **Repository:** `https://github.com/elapouya/python-docx-template` (Stars: 3.5k+)
- **Architecture:** Unzips `.docx` archives, parses `document.xml` using Jinja2 tags (`{{ variable }}`, `{% for row in items %}`), and reassembles the Office OpenXML package.
- **Key Strengths:**
  - Separates design from logic: Designers format the Word template; code only populates data.
  - Native support for sub-documents, dynamic tables, inline images, and rich text runs.
- **Project Adoption:**
  - Shallow cloned into [`tools/docxtpl/`](file:///c:/Users/Nguyen%20Trong%20Khoi/Downloads/CLOUD/tools/docxtpl).

---

### ⭐️ Repo 2: `python-openxml/python-docx`
- **Repository:** `https://github.com/python-openxml/python-docx` (Stars: 6.8k+)
- **Architecture:** Low-level object model for creating and modifying ECMA-376 `.docx` files.
- **Key Strengths:**
  - Granular control over XML elements: Margins (`left_margin`, `top_margin`), table cell shading (`w:shd`), paragraph borders, and section breaks.
  - Zero external dependencies: Does not require Microsoft Word or LibreOffice.
- **Project Adoption:**
  - Used in conjunction with `uit_report_content.py` in `scripts/generate_docx_report.py` to enforce the exact UIT thesis formatting rules.

---

### ⭐️ Repo 3: `jgm/pandoc` (Universal Document Converter)
- **Repository:** `https://github.com/jgm/pandoc` (Stars: 36k+)
- **Architecture:** Haskell-based AST document converter with custom `--reference-doc` styling.
- **Key Strengths:**
  - Seamless compilation from Markdown / LaTeX into formatted Word documents.
  - Automatic cross-referencing and IEEE bibliography citation management via `pandoc-citeproc`.

---

## 3. Comparative Architectural Matrix

| Paradigm | `python-docx-template` (docxtpl) | `python-docx` (Procedural) | `pandoc` (Converter) |
| :--- | :---: | :---: | :---: |
| **Primary Mechanism** | Jinja2 tag interpolation | OpenXML DOM API | AST parsing & reference doc |
| **Design / Logic Separation** | Complete (Word template) | Mixed in Python code | Complete (Markdown + Reference) |
| **XML Granularity** | Medium | Extreme | Low (limited to styles) |
| **Binary Dependencies** | Pure Python | Pure Python | Haskell Binary |
| **Role in Project** | **Cloned in `tools/docxtpl`** | **Generates UIT 6-chapter report** | Documented standard |

---

## 4. Implementation in ChurnGuard (UIT 6-Chapter Standard)
The project synthesizes these paradigms into a robust generation pipeline:
- **Module Separation:** Separated content (`scripts/uit_report_content.py`) from formatting logic (`scripts/generate_docx_report.py`) to satisfy the strict 400-line code cap.
- **Strict UIT Compliance:** Configured binding margins (Left 3.0cm, Right 2.0cm, Top 2.5cm, Bottom 2.5cm), Times New Roman 13pt typography, 1.5 line spacing, 300 DPI figure embedding, and IEEE references.
