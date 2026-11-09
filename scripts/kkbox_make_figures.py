"""Render report-ready SVG figures from matching KKBox aggregate reports.

The default gate refuses pilot data. --allow-pilot is only for local layout QA;
its output is visibly watermarked and must not be used as final evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def text(x: int, y: int, value: object, size: int = 16, color: str = "#eaf3fb",
         weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" '
        f'font-family="Segoe UI,Arial,sans-serif">{escape(str(value))}</text>'
    )


def rect(x: float, y: float, width: float, height: float, fill: str,
         radius: int = 0, stroke: str = "none") -> str:
    return (f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
            f'rx="{radius}" fill="{fill}" stroke="{stroke}"/>')


def svg(width: int, height: int, parts: list[str], title: str, pilot: bool) -> str:
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{escape(title)}">', f"<title>{escape(title)}</title>",
            rect(0, 0, width, height, "#0d1829"), *parts]
    if pilot:
        body += [rect(0, height - 42, width, 42, "#744239"),
                 text(20, height - 15, "PILOT / INCOMPLETE SOURCE — NOT FINAL EVIDENCE",
                      14, "#fff2df", 700)]
    return "\n".join([*body, "</svg>", ""])


def figure_model(report: dict, pilot: bool) -> str:
    parts = [text(40, 55, "SO SÁNH MODEL / VALIDATION THÁNG 02", 20, weight=700),
             text(40, 83, "PR-AUC · chọn model trước khi xem final test tháng 03", 13, "#9ab4c5")]
    candidates = sorted(report["candidate_validation"].items(),
                        key=lambda item: item[1]["pr_auc"], reverse=True)
    if not candidates:
        raise ValueError("Model report has no validation candidates")
    for index, (name, values) in enumerate(candidates):
        score = float(values["pr_auc"])
        if not 0 <= score <= 1:
            raise ValueError("Invalid PR-AUC")
        y = 135 + index * 104
        parts += [text(40, y, name.replace("_", " ").title(), 16, weight=600),
                  rect(40, y + 16, 610, 23, "#25394d", 7),
                  rect(40, y + 16, max(3, score * 610), 23,
                       "#7ee0c7" if name == report["model"] else "#6788d8", 7),
                  text(665, y + 35, f"{score:.4f}", 18, "#eaf3fb", 700)]
    parts += [text(40, 387, "CHAMPION", 12, "#8ddfca", 700),
              text(40, 416, report["model"].replace("_", " ").title(), 22, weight=700),
              text(40, 455, f'Model version: {report["model_version"]}', 12, "#9ab4c5")]
    return svg(760, 510, parts, "KKBox validation model comparison", pilot)


def figure_confusion(report: dict, pilot: bool) -> str:
    matrix = report["test"]["confusion_matrix"]
    if len(matrix) != 2 or any(len(row) != 2 for row in matrix):
        raise ValueError("Confusion matrix must be 2x2")
    parts = [text(40, 55, "FINAL TEST / THÁNG 03", 20, weight=700),
             text(40, 83, "Confusion matrix · hàng: nhãn thật · cột: dự đoán", 13, "#9ab4c5"),
             text(262, 130, "DỰ ĐOÁN 0", 12, "#9ab4c5", 700, "middle"),
             text(500, 130, "DỰ ĐOÁN 1", 12, "#9ab4c5", 700, "middle")]
    for row in range(2):
        y = 150 + row * 145
        parts.append(text(70, y + 78, f"NHÃN {row}", 13, "#9ab4c5", 700))
        for col in range(2):
            x = 150 + col * 240
            value = int(matrix[row][col])
            if value < 0:
                raise ValueError("Negative confusion matrix count")
            parts += [rect(x, y, 220, 125, "#1d514f" if row == col else "#5e3b42", 12),
                      text(x + 110, y + 75, f"{value:,}", 30, weight=750, anchor="middle")]
    parts += [text(40, 480, f'PR-AUC: {float(report["test"]["pr_auc"]):.4f}', 16, "#8ddfca", 700),
              text(285, 480, f'ROC-AUC: {float(report["test"]["roc_auc"]):.4f}', 16, "#9db5ec", 700),
              text(40, 515, f'Test rows: {int(report["test_rows"]):,}', 12, "#9ab4c5")]
    return svg(760, 565, parts, "KKBox final test confusion matrix", pilot)


def figure_drift(report: dict, pilot: bool) -> str:
    features = sorted(report["features"].items(),
                      key=lambda item: float(item[1]["psi"]), reverse=True)
    height = 150 + max(1, len(features)) * 42 + 70
    parts = [text(40, 52, "DRIFT / THÁNG 02 → THÁNG 03", 20, weight=700),
             text(40, 80, "Population Stability Index · ngưỡng cờ 0,20", 13, "#9ab4c5")]
    for index, (name, values) in enumerate(features):
        score = float(values["psi"])
        if score < 0:
            raise ValueError("Negative PSI")
        y = 126 + index * 42
        parts += [text(40, y + 16, name, 12, "#c7d9e6"),
                  rect(280, y, 350, 22, "#25394d", 5),
                  rect(280, y, min(score / .5, 1) * 350, 22,
                       "#f4a882" if values["drift_flag"] else "#79dac4", 5),
                  text(650, y + 17, f"{score:.3f}", 13, weight=700)]
    parts += [text(40, height - 65, f'Flagged features: {len(report["flagged_features"])}',
                   14, "#9ab4c5", 700)]
    return svg(760, height, parts, "KKBox historical feature drift", pilot)


def figure_pr_curve(report: dict, pilot: bool) -> str:
    curve = report.get("test_pr_curve")
    parts = [text(40, 55, "PRECISION–RECALL / FINAL TEST THÁNG 03", 20, weight=700),
             text(40, 83, "Đường hiển thị lấy mẫu tối đa 201 điểm; PR-AUC tính từ toàn bộ dự đoán",
                  12, "#9ab4c5")]
    if curve is None:
        if not pilot:
            raise ValueError("Full model report is missing test_pr_curve")
        parts.append(text(40, 240, "Pilot report cũ chưa lưu PR curve", 18, "#f3d38c", 700))
        return svg(760, 510, parts, "KKBox precision recall curve", pilot)
    recalls = curve["recall"]
    precisions = curve["precision"]
    if len(recalls) != len(precisions) or len(recalls) < 2:
        raise ValueError("Invalid PR curve arrays")
    if any(not 0 <= float(value) <= 1 for value in [*recalls, *precisions]):
        raise ValueError("PR curve value out of range")
    left, top, size = 95, 115, 335
    baseline = float(report["test"]["positive_rate"])
    parts += [rect(left, top, size, size, "#14273c", 8, "#47667d"),
              f'<line x1="{left}" y1="{top + (1-baseline)*size:.1f}" '
              f'x2="{left+size}" y2="{top + (1-baseline)*size:.1f}" '
              'stroke="#e5ae82" stroke-width="2" stroke-dasharray="6 6"/>',
              text(left, top + size + 28, "0", 11, "#9ab4c5"),
              text(left + size, top + size + 28, "1", 11, "#9ab4c5", anchor="end"),
              text(left + size / 2, top + size + 42, "RECALL", 12, "#9ab4c5", 700, "middle"),
              text(left - 30, top + 10, "1", 11, "#9ab4c5"),
              text(left - 30, top + size, "0", 11, "#9ab4c5")]
    points = " ".join(f"{left + float(r)*size:.1f},{top + (1-float(p))*size:.1f}"
                      for r, p in zip(recalls, precisions))
    parts.append(f'<polyline points="{points}" fill="none" stroke="#81e3c9" '
                 'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    parts += [text(485, 190, "PR-AUC", 12, "#9ab4c5", 700),
              text(485, 225, f'{float(report["test"]["pr_auc"]):.4f}', 28, "#8de7ce", 750),
              text(485, 290, "TỶ LỆ CHURN NỀN", 12, "#9ab4c5", 700),
              text(485, 325, f"{baseline:.2%}", 24, "#e5ae82", 700)]
    return svg(760, 525, parts, "KKBox precision recall curve", pilot)


def validate(audit: dict, model: dict, drift: dict, allow_pilot: bool) -> bool:
    model_mode = "full" if model.get("mode") == "full_cohort" else model.get("mode")
    drift_mode = "full" if drift.get("mode") == "full_cohort" else drift.get("mode")
    if model_mode != drift_mode:
        raise ValueError("Model and drift modes differ")
    pilot = model_mode == "pilot"
    if pilot and not allow_pilot:
        raise ValueError("Pilot reports cannot be rendered as final figures; use --allow-pilot only for layout QA")
    if not pilot and model_mode != "full":
        raise ValueError("Unknown report mode")
    if len({audit.get("source_revision_sha"), model.get("source_revision_sha"),
            drift.get("source_revision_sha")}) != 1:
        raise ValueError("Source revisions differ")
    if not pilot and (audit.get("status") != "full_cohort" or
                      not audit.get("complete_source") or
                      audit.get("input_file_count") != 32 or
                      audit.get("input_bytes", 0) < 4_000_000_000):
        raise ValueError("ETL audit does not prove full >4 GB processing")
    return pilot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--etl-audit", type=Path, default=Path("docs/experiments/kkbox_etl_audit.json"))
    parser.add_argument("--model-report", type=Path, default=Path("docs/experiments/kkbox_model_report.json"))
    parser.add_argument("--drift-report", type=Path, default=Path("docs/experiments/kkbox_drift_report.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/kkbox_figures"))
    parser.add_argument("--allow-pilot", action="store_true", help="Watermarked local layout QA only")
    args = parser.parse_args()
    audit, model, drift = (read_json(path) for path in
                           (args.etl_audit, args.model_report, args.drift_report))
    pilot = validate(audit, model, drift, args.allow_pilot)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figures = {
        "kkbox_model_comparison.svg": figure_model(model, pilot),
        "kkbox_confusion_matrix.svg": figure_confusion(model, pilot),
        "kkbox_pr_curve.svg": figure_pr_curve(model, pilot),
        "kkbox_drift.svg": figure_drift(drift, pilot),
    }
    for name, content in figures.items():
        (args.output_dir / name).write_text(content, encoding="utf-8")
    print(json.dumps({"mode": model["mode"], "figures": [str(args.output_dir / name)
                                                      for name in figures]}, indent=2))


if __name__ == "__main__":
    main()
