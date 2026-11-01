/**
 * ChurnGuard MLOps - Interactive Visualization Engine (Chart.js)
 * Cung cấp biểu đồ trực quan hóa so sánh mô hình và tiến trình tối ưu hóa siêu tham số.
 */

let modelChartInstance = null;
let optunaChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  initInteractiveCharts();
});

function getChartApiBase() {
  return window.API_BASE || ((window.location.protocol.startsWith("http") && window.location.origin && window.location.origin !== "null") ? window.location.origin : "http://localhost:8000");
}

function showChartOfflineNotice(canvasId, msg = "Chưa kết nối API (Port 8000)") {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !canvas.parentElement) return;
  const parent = canvas.parentElement;
  let notice = parent.querySelector(".chart-offline-notice");
  if (!notice) {
    notice = document.createElement("div");
    notice.className = "chart-offline-notice";
    parent.style.position = "relative";
    notice.style.cssText = "position:absolute;top:0;left:0;width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(15,23,42,0.88);color:#94A3B8;font-size:12px;font-weight:600;border-radius:8px;z-index:5;";
    notice.innerHTML = `<span style="color:#EF4444;font-size:13px;font-weight:700;margin-bottom:4px;">[CẢNH BÁO] Mất Kết Nối Backend API</span><span>${msg}</span>`;
    parent.appendChild(notice);
  }
}

function clearChartOfflineNotice(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !canvas.parentElement) return;
  const notice = canvas.parentElement.querySelector(".chart-offline-notice");
  if (notice) notice.remove();
}

async function initInteractiveCharts() {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js chua duoc tai.");
    return;
  }
  Chart.defaults.color = "#94A3B8";
  Chart.defaults.font.family = "'Inter', sans-serif";
  await renderModelMetricsChart();
  await renderOptunaConvergenceChart();
}

async function renderModelMetricsChart() {
  const canvas = document.getElementById("chartModelMetrics");
  if (!canvas) return;

  const modelData = {
    labels: ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"],
    datasets: [
      { label: "XGBoost (Champion)", data: [], backgroundColor: "rgba(16, 185, 129, 0.75)", borderColor: "#10B981", borderWidth: 1.5, borderRadius: 4 },
      { label: "Random Forest", data: [], backgroundColor: "rgba(14, 165, 233, 0.75)", borderColor: "#0EA5E9", borderWidth: 1.5, borderRadius: 4 },
      { label: "LightGBM", data: [], backgroundColor: "rgba(245, 158, 11, 0.75)", borderColor: "#F59E0B", borderWidth: 1.5, borderRadius: 4 },
      { label: "Logistic Regression", data: [], backgroundColor: "rgba(148, 163, 184, 0.6)", borderColor: "#94A3B8", borderWidth: 1.5, borderRadius: 4 }
    ]
  };

  try {
    const res = await fetch(`${getChartApiBase()}/models/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json && json.models) {
      clearChartOfflineNotice("chartModelMetrics");
      const m = json.models;
      const champ = (json.champion_model || "XGBoost").replace("_", " ");
      modelData.datasets.forEach(ds => {
        ds.label = ds.label.includes(champ) ? `${champ} (Champion)` : ds.label.replace(" (Champion)", "");
      });
      if (m.XGBoost) modelData.datasets[0].data = [m.XGBoost.test.accuracy, m.XGBoost.test.precision, m.XGBoost.test.recall, m.XGBoost.test.f1_score, m.XGBoost.test.roc_auc];
      if (m.Random_Forest) modelData.datasets[1].data = [m.Random_Forest.test.accuracy, m.Random_Forest.test.precision, m.Random_Forest.test.recall, m.Random_Forest.test.f1_score, m.Random_Forest.test.roc_auc];
      if (m.LightGBM) modelData.datasets[2].data = [m.LightGBM.test.accuracy, m.LightGBM.test.precision, m.LightGBM.test.recall, m.LightGBM.test.f1_score, m.LightGBM.test.roc_auc];
      if (m.Logistic_Regression) modelData.datasets[3].data = [m.Logistic_Regression.test.accuracy, m.Logistic_Regression.test.precision, m.Logistic_Regression.test.recall, m.Logistic_Regression.test.f1_score, m.Logistic_Regression.test.roc_auc];
    } else {
      throw new Error("Invalid model payload");
    }
  } catch (e) {
    showChartOfflineNotice("chartModelMetrics", "Dịch vụ FastAPI chưa khả dụng trên cổng 8000");
  }

  if (modelChartInstance) modelChartInstance.destroy();
  modelChartInstance = new Chart(canvas, {
    type: "bar",
    data: modelData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: { backgroundColor: "#1E293B", titleColor: "#F8FAFC", bodyColor: "#CBD5E1", borderColor: "#334155", borderWidth: 1 }
      },
      scales: {
        y: { min: 0.8, max: 1.0, grid: { color: "#1E293B" }, ticks: { font: { size: 10 } } },
        x: { grid: { display: false }, ticks: { font: { size: 10 } } }
      }
    }
  });
}

async function renderOptunaConvergenceChart() {
  const canvas = document.getElementById("chartOptunaConvergence");
  if (!canvas) return;

  const trialLabels = [];
  const trialScores = [];
  const bestScores = [];

  try {
    const res = await fetch(`${getChartApiBase()}/models/tuning`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    const trials = json?.xgboost_champion?.trials_history;
    if (Array.isArray(trials) && trials.length > 0) {
      clearChartOfflineNotice("chartOptunaConvergence");
      let runningBest = 0;
      trials.forEach((t, idx) => {
        trialLabels.push(`T${idx + 1}`);
        trialScores.push(t.value);
        runningBest = Math.max(runningBest, t.value);
        bestScores.push(runningBest);
      });
    } else {
      throw new Error("Empty trials payload");
    }
  } catch (e) {
    showChartOfflineNotice("chartOptunaConvergence", "Dịch vụ FastAPI chưa khả dụng trên cổng 8000");
  }

  if (optunaChartInstance) optunaChartInstance.destroy();
  optunaChartInstance = new Chart(canvas, {
    type: "line",
    data: {
      labels: trialLabels,
      datasets: [
        { label: "Giá trị Trial (ROC-AUC)", data: trialScores, borderColor: "#38BDF8", backgroundColor: "rgba(56, 189, 248, 0.15)", pointRadius: 4, pointBackgroundColor: "#38BDF8", tension: 0.2 },
        { label: "Điểm Tối Ưu Tích Lũy (Best ROC-AUC)", data: bestScores, borderColor: "#10B981", borderDash: [5, 5], pointRadius: 0, fill: false, tension: 0 }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: { backgroundColor: "#1E293B", titleColor: "#F8FAFC", bodyColor: "#CBD5E1", borderColor: "#334155", borderWidth: 1 }
      },
      scales: {
        y: { min: 0.995, max: 1.0, grid: { color: "#1E293B" }, ticks: { font: { size: 10 } } },
        x: { grid: { color: "#1E293B" }, ticks: { font: { size: 10 } } }
      }
    }
  });
}
