/**
 * ChurnGuard MLOps - Interactive Visualization Engine (Chart.js)
 * Cung cap bieu do truc quan dong cho So sanh Mo hinh va Toi uu hoa Optuna.
 * Tuan thu Invariant 02, Invariant 05 va Invariant 06 (< 200 dong).
 */

let modelChartInstance = null;
let optunaChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  initInteractiveCharts();
});

function getChartApiBase() {
  return window.API_BASE || ((window.location.protocol.startsWith("http") && window.location.origin && window.location.origin !== "null") ? window.location.origin : "http://localhost:8000");
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
      { label: "XGBoost (Champion)", data: [0.9983, 0.9981, 0.9989, 0.9985, 0.9990], backgroundColor: "rgba(16, 185, 129, 0.75)", borderColor: "#10B981", borderWidth: 1.5, borderRadius: 4 },
      { label: "Random Forest", data: [0.9940, 0.9999, 0.9895, 0.9947, 0.9988], backgroundColor: "rgba(14, 165, 233, 0.75)", borderColor: "#0EA5E9", borderWidth: 1.5, borderRadius: 4 },
      { label: "LightGBM", data: [0.9996, 1.0000, 0.9993, 0.9997, 0.9999], backgroundColor: "rgba(245, 158, 11, 0.75)", borderColor: "#F59E0B", borderWidth: 1.5, borderRadius: 4 },
      { label: "Logistic Regression", data: [0.8717, 0.9155, 0.8523, 0.8828, 0.9445], backgroundColor: "rgba(148, 163, 184, 0.6)", borderColor: "#94A3B8", borderWidth: 1.5, borderRadius: 4 }
    ]
  };

  try {
    const res = await fetch(`${getChartApiBase()}/models/summary`);
    if (res.ok) {
      const json = await res.json();
      if (json && json.models) {
        const m = json.models;
        const champ = (json.champion_model || "XGBoost").replace("_", " ");
        modelData.datasets.forEach(ds => {
          ds.label = ds.label.includes(champ) ? `${champ} (Champion)` : ds.label.replace(" (Champion)", "");
        });
        if (m.XGBoost) modelData.datasets[0].data = [m.XGBoost.test.accuracy, m.XGBoost.test.precision, m.XGBoost.test.recall, m.XGBoost.test.f1_score, m.XGBoost.test.roc_auc];
        if (m.Random_Forest) modelData.datasets[1].data = [m.Random_Forest.test.accuracy, m.Random_Forest.test.precision, m.Random_Forest.test.recall, m.Random_Forest.test.f1_score, m.Random_Forest.test.roc_auc];
        if (m.LightGBM) modelData.datasets[2].data = [m.LightGBM.test.accuracy, m.LightGBM.test.precision, m.LightGBM.test.recall, m.LightGBM.test.f1_score, m.LightGBM.test.roc_auc];
        if (m.Logistic_Regression) modelData.datasets[3].data = [m.Logistic_Regression.test.accuracy, m.Logistic_Regression.test.precision, m.Logistic_Regression.test.recall, m.Logistic_Regression.test.f1_score, m.Logistic_Regression.test.roc_auc];
      }
    }
  } catch (e) {}

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

  const trialLabels = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"];
  const trialScores = [0.9989, 0.9985, 0.9989, 0.9980, 0.9983, 0.9989, 0.9978, 0.9987, 0.9961, 0.9990, 0.9989, 0.9990];
  const bestScores = [0.9989, 0.9989, 0.9989, 0.9989, 0.9989, 0.9989, 0.9989, 0.9989, 0.9989, 0.9990, 0.9990, 0.9990];

  try {
    const res = await fetch(`${getChartApiBase()}/models/tuning`);
    if (res.ok) {
      const json = await res.json();
      const trials = json?.xgboost_champion?.trials_history;
      if (Array.isArray(trials) && trials.length > 0) {
        trialLabels.length = 0;
        trialScores.length = 0;
        bestScores.length = 0;
        let runningBest = 0;
        trials.forEach((t, idx) => {
          trialLabels.push(`T${idx + 1}`);
          trialScores.push(t.value);
          runningBest = Math.max(runningBest, t.value);
          bestScores.push(runningBest);
        });
      }
    }
  } catch (e) {}

  if (optunaChartInstance) optunaChartInstance.destroy();
  optunaChartInstance = new Chart(canvas, {
    type: "line",
    data: {
      labels: trialLabels,
      datasets: [
        { label: "Giá trị Trial (ROC-AUC)", data: trialScores, borderColor: "#38BDF8", backgroundColor: "rgba(56, 189, 248, 0.15)", pointRadius: 4, pointBackgroundColor: "#38BDF8", tension: 0.2 },
        { label: "Best Objective So Far", data: bestScores, borderColor: "#10B981", borderDash: [5, 5], pointRadius: 0, fill: false, tension: 0 }
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
