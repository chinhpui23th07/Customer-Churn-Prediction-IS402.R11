/**
 * ChurnGuard MLOps Web App Frontend Logic
 * Kết nối REST API FastAPI, trực quan hóa rủi ro và xử lý batch.
 * Tuân thủ Invariant 01 và Invariant 02 (< 400 dòng).
 */
const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
  ? window.location.origin
  : "http://localhost:8000";

let currentBatchPredictions = [];

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  checkApiHealth();
  loadModelsSummary();
  loadDriftStatus();
  setupSinglePredictionForm();
  setupBatchUpload();
});

// 1. Quản lý Tab điều hướng
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");
    });
  });
}

// 2. Kiểm tra HealthCheck của API
async function checkApiHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("api-status-text").textContent = `FastAPI: ${data.status} (Online)`;
      document.getElementById("champion-name").textContent = data.champion_model;
      document.getElementById("kpi-model-name").textContent = data.champion_model;
    }
  } catch (err) {
    document.getElementById("api-status-text").textContent = "FastAPI: Offline (Chưa bật server)";
  }
}

// 3. Xử lý Form Dự Đoán Cá Nhân
function setupSinglePredictionForm() {
  const form = document.getElementById("prediction-form");
  const resultBox = document.getElementById("prediction-result");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-single");
    btn.textContent = "Đang Phân Tích...";
    btn.disabled = true;

    const payload = {
      customer_id: 88888,
      age: parseFloat(document.getElementById("age").value),
      gender: document.getElementById("gender").value,
      tenure: parseFloat(document.getElementById("tenure").value),
      usage_frequency: parseFloat(document.getElementById("usage_frequency").value),
      support_calls: parseFloat(document.getElementById("support_calls").value),
      payment_delay: parseFloat(document.getElementById("payment_delay").value),
      subscription_type: document.getElementById("subscription_type").value,
      contract_length: document.getElementById("contract_length").value,
      total_spend: parseFloat(document.getElementById("total_spend").value),
      last_interaction: parseFloat(document.getElementById("last_interaction").value)
    };

    try {
      const res = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("API trả về lỗi");
      const data = await res.json();
      renderSingleResult(data);
    } catch (err) {
      alert("Không thể kết nối đến FastAPI Serving Endpoint! Đảm bảo server đang chạy tại port 8000.");
    } finally {
      btn.textContent = "Phân Tích Nguy Cơ Rời Bỏ";
      btn.disabled = false;
    }
  });
}

function renderSingleResult(data) {
  const resultBox = document.getElementById("prediction-result");
  const badge = document.getElementById("risk-badge");
  const probDisplay = document.getElementById("prob-display");
  const gaugeFill = document.getElementById("gauge-fill");
  const latencyBadge = document.getElementById("result-latency");
  const recText = document.getElementById("recommendation-text");

  resultBox.classList.remove("hidden");
  const pct = (data.churn_probability * 100).toFixed(1);
  probDisplay.textContent = `${pct}%`;
  gaugeFill.style.width = `${pct}%`;
  latencyBadge.textContent = `${data.latency_ms} ms`;
  recText.textContent = data.recommended_action;

  badge.className = "risk-badge";
  if (data.churn_probability >= 0.70) {
    badge.classList.add("risk-high");
    badge.textContent = "RỦI RO CAO (HIGH RISK)";
    gaugeFill.style.background = "#EF4444";
  } else if (data.churn_probability >= 0.35) {
    badge.classList.add("risk-medium");
    badge.textContent = "RỦI RO TRUNG BÌNH (MEDIUM RISK)";
    gaugeFill.style.background = "#FBBF24";
  } else {
    badge.classList.add("risk-low");
    badge.textContent = "AN TOÀN (LOW RISK)";
    gaugeFill.style.background = "#10B981";
  }

  // Render Explainable AI (SHAP Lundberg & Lee 2017)
  const xaiSummary = document.getElementById("xai-summary-text");
  const xaiBars = document.getElementById("xai-bars");
  if (data.explanation_summary && xaiSummary) {
    xaiSummary.textContent = data.explanation_summary;
  }
  if (data.feature_attributions && xaiBars) {
    xaiBars.innerHTML = "";
    for (const [feature, weight] of Object.entries(data.feature_attributions)) {
      const barItem = document.createElement("div");
      barItem.className = "xai-bar-item";
      const wPct = Math.min(100, Math.max(5, (weight * 100))).toFixed(0);
      barItem.innerHTML = `
        <div class="xai-bar-row">
          <span class="xai-bar-label">${feature}</span>
          <span class="xai-bar-val">+${(weight * 100).toFixed(1)}%</span>
        </div>
        <div class="xai-bar-track">
          <div class="xai-bar-fill" style="width: ${wPct}%;"></div>
        </div>
      `;
      xaiBars.appendChild(barItem);
    }
  }
}

// 4. Xử lý Batch Upload & Dữ Liệu Mẫu
function setupBatchUpload() {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("csv-file-input");
  const browseBtn = document.getElementById("btn-browse-file");
  const sampleBtn = document.getElementById("btn-sample-batch");
  const downloadBtn = document.getElementById("btn-download-batch-csv");

  browseBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) uploadCsvFile(e.target.files[0]);
  });

  sampleBtn.addEventListener("click", sendSampleBatch);
  downloadBtn.addEventListener("click", downloadBatchCsv);
}

async function uploadCsvFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/upload_csv_predict`, {
      method: "POST",
      body: formData
    });
    if (!res.ok) throw new Error("Lỗi xử lý file CSV");
    const data = await res.json();
    renderBatchResults(data);
  } catch (err) {
    alert("Lỗi tải tệp CSV! Đảm bảo các cột đúng định dạng Kaggle Customer Churn.");
  }
}

async function sendSampleBatch() {
  const samples = [
    { customer_id: 101, age: 24, gender: "Male", tenure: 3, usage_frequency: 5, support_calls: 7, payment_delay: 14, subscription_type: "Basic", contract_length: "Monthly", total_spend: 150, last_interaction: 22 },
    { customer_id: 102, age: 52, gender: "Female", tenure: 40, usage_frequency: 24, support_calls: 1, payment_delay: 0, subscription_type: "Premium", contract_length: "Annual", total_spend: 1100, last_interaction: 3 },
    { customer_id: 103, age: 36, gender: "Male", tenure: 18, usage_frequency: 14, support_calls: 3, payment_delay: 4, subscription_type: "Standard", contract_length: "Quarterly", total_spend: 600, last_interaction: 10 },
    { customer_id: 104, age: 60, gender: "Female", tenure: 12, usage_frequency: 8, support_calls: 5, payment_delay: 9, subscription_type: "Basic", contract_length: "Monthly", total_spend: 320, last_interaction: 18 },
    { customer_id: 105, age: 29, gender: "Male", tenure: 30, usage_frequency: 28, support_calls: 0, payment_delay: 1, subscription_type: "Premium", contract_length: "Annual", total_spend: 950, last_interaction: 2 }
  ];

  try {
    const res = await fetch(`${API_BASE}/batch_predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(samples)
    });
    if (!res.ok) throw new Error("Lỗi API batch");
    const data = await res.json();
    renderBatchResults(data);
  } catch (err) {
    alert("Không thể gửi dữ liệu mẫu đến API.");
  }
}

function renderBatchResults(data) {
  currentBatchPredictions = data.predictions;
  const container = document.getElementById("batch-results-container");
  container.classList.remove("hidden");

  document.getElementById("batch-total").textContent = data.total_processed;
  document.getElementById("batch-churn").textContent = data.churn_count;
  document.getElementById("batch-stay").textContent = data.retention_count;
  document.getElementById("batch-rate").textContent = `${(data.overall_churn_rate * 100).toFixed(1)}%`;

  const tbody = document.getElementById("batch-tbody");
  tbody.innerHTML = "";

  data.predictions.slice(0, 10).forEach(p => {
    const tr = document.createElement("tr");
    const riskColor = p.risk_level === "High Risk" ? "#EF4444" : (p.risk_level === "Medium Risk" ? "#FBBF24" : "#10B981");
    tr.innerHTML = `
      <td style="font-weight:600;color:#F8FAFC;">#${p.customer_id}</td>
      <td style="font-weight:700;">${(p.churn_probability * 100).toFixed(1)}%</td>
      <td><span style="color:${riskColor};font-weight:600;">${p.risk_level}</span></td>
      <td style="font-size:12px;color:#94A3B8;">${p.recommended_action}</td>
    `;
    tbody.appendChild(tr);
  });
}

function downloadBatchCsv() {
  if (currentBatchPredictions.length === 0) return;
  let csv = "CustomerID,ChurnPrediction,ChurnProbability,RiskLevel,RecommendedAction\n";
  currentBatchPredictions.forEach(p => {
    csv += `"${p.customer_id}","${p.churn_prediction}","${p.churn_probability}","${p.risk_level}","${p.recommended_action.replace(/"/g, '""')}"\n`;
  });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `churn_predictions_annotated_${Date.now()}.csv`;
  a.click();
}

// 5. Tải dữ liệu Bảng So Sánh Mô Hình & Drift
async function loadModelsSummary() {
  try {
    const res = await fetch(`${API_BASE}/models/summary`);
    if (res.ok) {
      const data = await res.json();
      const tbody = document.getElementById("models-tbody");
      if (!tbody) return;
      tbody.innerHTML = "";
      for (const [name, info] of Object.entries(data.models)) {
        const tr = document.createElement("tr");
        const t = info.test;
        const isChamp = (name === data.champion_model) ? " <strong style='color:#F59E0B;'>(Champion)</strong>" : "";
        tr.innerHTML = `
          <td style="font-weight:600;color:#F8FAFC;">${name.replace("_", " ")}${isChamp}</td>
          <td>${t.accuracy.toFixed(4)}</td>
          <td>${t.precision.toFixed(4)}</td>
          <td>${t.recall.toFixed(4)}</td>
          <td>${t.f1_score.toFixed(4)}</td>
          <td style="font-weight:700;color:#10B981;">${t.roc_auc.toFixed(4)}</td>
        `;
        tbody.appendChild(tr);
      }
    }
  } catch (err) {}
}

async function loadDriftStatus() {
  try {
    const res = await fetch(`${API_BASE}/drift/status`);
    if (res.ok) {
      const data = await res.json();
      const tbody = document.getElementById("drift-table");
      if (!tbody) return;
      tbody.innerHTML = "";
      for (const [feat, info] of Object.entries(data.features)) {
        const tr = document.createElement("tr");
        const badgeColor = info.drift_level === "Stable" ? "#10B981" : (info.drift_level === "Moderate" ? "#F59E0B" : "#EF4444");
        tr.innerHTML = `
          <td style="font-weight:600;color:#F8FAFC;">${feat}</td>
          <td>${info.ks_statistic}</td>
          <td>${info.p_value}</td>
          <td>${info.psi_score}</td>
          <td><span style="color:${badgeColor};font-weight:600;">${info.drift_level}</span></td>
        `;
        tbody.appendChild(tr);
      }
    }
  } catch (err) {}
}
