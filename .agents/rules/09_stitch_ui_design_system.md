---
id: rule-09-stitch-ui-design-system
title: Google Stitch UI Design System & Bento Grid Standard
activation: always_on
description: "Governs modern, bespoke web interfaces with Bento Grid layouts, DESIGN.md design systems, and presentation components under 200 lines."
---

# Rule 09: Google Stitch UI Design System & Bento Grid Standard

## 1. Design System Blueprint (`DESIGN.md`)
Every user interface must be governed by a root `DESIGN.md` specification detailing:
- Color Tokens: Oceanic Navy (`#0A192F`), Amber (`#F59E0B`), Forest Emerald (`#10B981`).
- Typography: Inter / Roboto Google Fonts hierarchy.
- Surface Elevations: Glassmorphism translucent backdrops with subtle border glow.

---

## 2. Bento Grid Layout
- Group operational features into modular cards within a responsive CSS grid.
- Provide comprehensive states: Loading skeletons, active gauges, and empty data placeholders.
- Maintain strict component separation: Presentation components < 200 lines, custom API hooks < 150 lines.
