"""
Module trực quan hóa và đánh giá chi tiết mô hình (Mục 4.3 của Rubric).
Xuất biểu đồ ROC Curve, Confusion Matrix và Feature Importance độ phân giải cao.
Tuân thủ Invariant 01 và Invariant 02 (< 400 dòng).
"""
import os
import sys
import json
import matplotlib.pyplot as plt
import seaborn as sns

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EVAL_RESULTS_FILE = os.path.join(BASE_DIR, "data", "models", "evaluation_results.json")
IMAGES_DIR = os.path.join(BASE_DIR, "docs", "images")


def setup_plot_style():
    """Thiết lập phong cách đồ họa chuyên nghiệp (Oceanic Palette)."""
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "sans-serif"]
    plt.rcParams["axes.edgecolor"] = "#CBD5E1"
    plt.rcParams["axes.linewidth"] = 1.0


def generate_evaluation_visualizations():
    """Tạo toàn bộ các đồ thị phân tích mô hình phục vụ báo cáo và web dashboard."""
    os.makedirs(IMAGES_DIR, exist_ok=True)

    with open(EVAL_RESULTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    models_data = data["models"]
    setup_plot_style()

    # 1. Biểu đồ so sánh các chỉ số (Accuracy, Precision, Recall, F1, ROC-AUC)
    metrics_names = ["accuracy", "precision", "recall", "f1_score", "roc_auc"]
    models_names = list(models_data.keys())

    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    x = range(len(metrics_names))
    width = 0.18

    colors = ["#64748B", "#0F766E", "#F59E0B", "#2563EB"]

    for idx, (m_name, color) in enumerate(zip(models_names, colors)):
        vals = [models_data[m_name]["test"][m] for m in metrics_names]
        pos = [p + (idx - 1.5) * width for p in x]
        bars = ax.bar(pos, vals, width, label=m_name.replace("_", " "), color=color, alpha=0.9, edgecolor="#1E293B", linewidth=0.5)
        for b in bars:
            height = b.get_height()
            ax.annotate(f"{height:.2f}",
                        xy=(b.get_x() + b.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7.5, fontweight="bold")

    ax.set_title("So Sánh Hiệu Năng Các Mô Hình Dự Đoán Customer Churn", fontsize=13, fontweight="bold", pad=15, color="#0A192F")
    ax.set_xticks(x)
    ax.set_xticklabels(["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"], fontsize=11, fontweight="600")
    ax.set_ylim(0.75, 1.05)
    ax.set_ylabel("Điểm Số (Score)", fontsize=11, fontweight="600")
    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor="#CBD5E1", loc="lower right")
    plt.tight_layout()
    chart1_path = os.path.join(IMAGES_DIR, "model_comparison_metrics.png")
    plt.savefig(chart1_path)
    plt.close()
    print(f"[+] Đã tạo đồ thị so sánh chỉ số: {chart1_path}")

    # 2. Biểu đồ ROC Curve
    fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
    for m_name, color in zip(models_names, colors):
        curve = models_data[m_name]["test"]["roc_curve"]
        fpr = [pt["fpr"] for pt in curve]
        tpr = [pt["tpr"] for pt in curve]
        auc_val = models_data[m_name]["test"]["roc_auc"]
        ax.plot(fpr, tpr, label=f"{m_name.replace('_', ' ')} (AUC = {auc_val:.4f})", color=color, linewidth=2.2)

    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Guess (AUC = 0.50)")
    ax.set_title("Đường Cong ROC (Receiver Operating Characteristic)", fontsize=13, fontweight="bold", pad=12, color="#0A192F")
    ax.set_xlabel("False Positive Rate (FPR)", fontsize=11, fontweight="600")
    ax.set_ylabel("True Positive Rate (TPR)", fontsize=11, fontweight="600")
    ax.legend(loc="lower right", frameon=True, facecolor="#F8FAFC")
    plt.tight_layout()
    chart2_path = os.path.join(IMAGES_DIR, "roc_curves.png")
    plt.savefig(chart2_path)
    plt.close()
    print(f"[+] Đã tạo đồ thị ROC Curves: {chart2_path}")

    # 3. Biểu đồ Confusion Matrix cho Champion Model
    champion = data["champion_model"]
    cm = models_data[champion]["test"]["confusion_matrix"]
    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Retained (0)", "Churned (1)"],
                yticklabels=["Retained (0)", "Churned (1)"],
                annot_kws={"size": 13, "weight": "bold"}, ax=ax)
    ax.set_title(f"Ma Trận Nhầm Lẫn - Champion ({champion.replace('_', ' ')})", fontsize=12, fontweight="bold", pad=12, color="#0A192F")
    ax.set_xlabel("Nhãn Dự Đoán (Predicted)", fontsize=11, fontweight="600")
    ax.set_ylabel("Nhãn Thực Tế (Actual)", fontsize=11, fontweight="600")
    plt.tight_layout()
    chart3_path = os.path.join(IMAGES_DIR, "confusion_matrix_champion.png")
    plt.savefig(chart3_path)
    plt.close()
    print(f"[+] Đã tạo Ma trận nhầm lẫn: {chart3_path}")

    # 4. Biểu đồ Feature Importance của Mô hình
    feat_imp = models_data[champion]["feature_importance"]
    if feat_imp:
        sorted_feats = sorted(feat_imp.items(), key=lambda x: x[1], reverse=True)
        f_names = [k for k, _ in sorted_feats]
        f_vals = [v for _, v in sorted_feats]

        fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
        bars = ax.barh(f_names[::-1], f_vals[::-1], color="#0F766E", edgecolor="#134E4A", alpha=0.85)
        for b in bars:
            width_b = b.get_width()
            ax.annotate(f"{width_b:.4f}",
                        xy=(width_b, b.get_y() + b.get_height() / 2),
                        xytext=(4, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=8, fontweight="bold", color="#0F172A")

        ax.set_title(f"Độ Quan Trọng Của Đặc Trưng (Feature Importance - {champion})", fontsize=12, fontweight="bold", pad=12, color="#0A192F")
        ax.set_xlabel("Mức Độ Đóng Góp (Importance Score)", fontsize=11, fontweight="600")
        ax.set_xlim(0, max(f_vals) * 1.15)
        plt.tight_layout()
        chart4_path = os.path.join(IMAGES_DIR, "feature_importance.png")
        plt.savefig(chart4_path)
        plt.close()
        print(f"[+] Đã tạo đồ thị Feature Importance: {chart4_path}")

    # Xuất báo cáo tổng kết JSON phục vụ DVC pipeline và Dashboard
    report_json = os.path.join(BASE_DIR, "data", "processed", "model_evaluation_report.json")
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump({
            "champion_model": champion,
            "metrics": models_data[champion]["test"],
            "charts": [
                "docs/images/model_comparison_metrics.png",
                "docs/images/roc_curves.png",
                "docs/images/confusion_matrix_champion.png",
                "docs/images/feature_importance.png"
            ]
        }, f, indent=2, ensure_ascii=False)
    print(f"[+] Đã lưu báo cáo đánh giá mô hình tại: {report_json}")


if __name__ == "__main__":
    generate_evaluation_visualizations()
