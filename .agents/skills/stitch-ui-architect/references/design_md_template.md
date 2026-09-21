# Google Stitch DESIGN.md Template

Mau chuan file `DESIGN.md` dat tai thu muc goc frontend de dinh hinh toan bo ngon ngu thiet ke:

```markdown
# Design System Specification (Google Stitch Standard)

## 1. Visual Philosophy & Core Aesthetic
- **Design Metaphor:** Modern Bento Grid with Precision Clean Surface.
- **Atmosphere:** Deep Oceanic Slate dark mode, breathable space, high contrast accessibility.
- **Motion:** Subtle micro-interactions (200ms - 300ms ease-out) providing fluid tactile feedback.
- **Strict Anti-AI Cliché Rule:** Khong dung tong mau tim den AI. Khong dung icon tho so. Dung dau '-' chuan ban phim.

---

## 2. Color Tokens (Domain-Grounded Palette - No Cliché Purple)

| Token Name | HEX / HSL | Cong Dung |
| :--- | :--- | :--- |
| `--bg-base` | `#0A1128` | Nen trang tong the (Deep Oceanic Navy) |
| `--bg-surface` | `rgba(255, 255, 255, 0.04)` | The kinh mo (Bento Cards) |
| `--bg-surface-hover`| `rgba(255, 255, 255, 0.07)` | Trang thai hover the |
| `--border-subtle` | `rgba(2, 132, 199, 0.18)` | Duong vien sieu mong giua cac khoi |
| `--primary-accent` | `#0284C7` (Cobalt Sky) | Nut bam chinh, lien ket, highlight |
| `--secondary-accent`| `#38BDF8` (Bright Azure) | Diem nhan phu, tag, badge |
| `--success-accent` | `#059669` (Emerald) | Xac nhan thanh cong, tang truong |
| `--warning-accent` | `#D97706` (Warm Amber) | Canh bao, trang thai cho |
| `--text-primary` | `#F8FAFC` | Tieu de va van ban chinh |
| `--text-secondary` | `#94A3B8` | Chu thich, nhan phu, thong so |

---

## 3. Typography & Hierarchy
- **Primary Headings:** 'Plus Jakarta Sans', sans-serif (Font Weight: 600, 700).
- **Body Text & Numbers:** 'Inter', sans-serif (Font Weight: 400, 500).
- **Code & Hashes:** 'JetBrains Mono', monospace.

---

## 4. Layout & Surface Elevation
- **Card Border Radius:** 16px (rounded-2xl).
- **Inner Padding:** 24px (p-6).
- **Backdrop Blur:** blur(12px).
- **Card Elevation:** box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.4).

---

## 5. Micro-Animations & Interactions
- Hover Cards: transform: translateY(-2px); transition: all 0.2s ease-out;
- Buttons: Hieu ung active thu nho nhe active:scale-[0.98].
- Skeleton: Shimmer animation trong chu ky 1.5s.
- Icons: 100% dung icon vector tu Lucide, Iconsax hoac custom SVG (assets/logo.svg).
```
