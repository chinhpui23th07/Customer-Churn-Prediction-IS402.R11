const form = document.getElementById('prediction-form');
const errorBox = document.getElementById('form-error');
const submitButton = document.getElementById('submit-button');
const statusBox = document.getElementById('system-status');
const statusText = document.getElementById('system-status-text');
const resultState = document.getElementById('result-state');
const riskLabels = {low: 'RỦI RO THẤP', medium: 'RỦI RO TRUNG BÌNH', high: 'RỦI RO CAO'};
const maxUint64 = 18446744073709551615n;

function validSubscriberKey(value) {
  return /^(0|[1-9][0-9]*)$/.test(value) && value.length <= 20 && BigInt(value) <= maxUint64;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  resultState.textContent = 'CẦN KIỂM TRA INPUT';
  resultState.classList.remove('active');
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = '';
}

function explainHttpError(response, data) {
  if (response.status === 401) return 'Mã truy cập demo chưa đúng. Hãy kiểm tra và thử lại.';
  if (response.status === 404) return 'Không có snapshot của khách hàng này tại ngày chốt đã chọn.';
  if (response.status === 422) return 'Subscriber key hoặc ngày chốt không hợp lệ.';
  if (response.status === 503) return 'Model hoặc Feature Store chưa sẵn sàng. Hãy kiểm tra trạng thái hệ thống.';
  if (typeof data.detail === 'string') return data.detail;
  return 'API trả về lỗi HTTP ' + response.status + '.';
}

function renderResult(data) {
  const probability = Number(data.churn_probability);
  if (!Number.isFinite(probability) || probability < 0 || probability > 1 ||
      !Object.hasOwn(riskLabels, data.risk_level) || ![0, 1].includes(data.prediction)) {
    throw new Error('Phản hồi API không đúng định dạng dự đoán.');
  }
  const percent = probability * 100;
  document.getElementById('result-empty').hidden = true;
  document.getElementById('result-data').hidden = false;
  document.getElementById('score-ring').style.setProperty('--score', percent + '%');
  document.getElementById('score-value').textContent = percent.toFixed(1) + '%';
  document.getElementById('meter-fill').style.width = percent + '%';
  document.getElementById('prediction-label').textContent = data.prediction === 1 ? 'Có nguy cơ rời bỏ' : 'Dự đoán tiếp tục';
  const badge = document.getElementById('risk-badge');
  badge.className = 'risk-badge ' + data.risk_level;
  badge.textContent = riskLabels[data.risk_level];
  document.getElementById('result-cutoff').textContent = data.as_of_date;
  document.getElementById('result-model').textContent = String(data.model_version);
  document.getElementById('result-feature').textContent = String(data.feature_version);
  resultState.textContent = 'DỰ ĐOÁN HOÀN TẤT';
  resultState.classList.add('active');
}

async function checkHealth() {
  try {
    const response = await fetch('/health', {cache: 'no-store'});
    if (!response.ok) throw new Error('Health request failed');
    const data = await response.json();
    statusBox.classList.toggle('ready', data.status === 'ready');
    statusBox.classList.toggle('degraded', data.status !== 'ready');
    statusText.textContent = data.status === 'ready'
      ? (data.mode === 'pilot' ? 'PILOT' : 'FULL') + ' · MODEL ' + data.model_version
      : 'MODEL CHƯA SẴN SÀNG';
  } catch {
    statusBox.classList.add('degraded');
    statusText.textContent = 'KHÔNG KẾT NỐI API';
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  clearError();
  const subscriber_key = document.getElementById('subscriber-key').value.trim();
  const as_of_date = document.getElementById('as-of-date').value;
  const apiKey = document.getElementById('api-key').value;
  if (!validSubscriberKey(subscriber_key)) return showError('Subscriber key phải là chuỗi số thập phân chuẩn trong phạm vi uint64.');
  if (!['2017-01-31', '2017-02-28'].includes(as_of_date)) return showError('Ngày chốt không được hỗ trợ.');
  if (!apiKey) return showError('Hãy nhập mã truy cập demo.');
  submitButton.disabled = true;
  submitButton.firstElementChild.textContent = 'Đang tính toán...';
  resultState.textContent = 'ĐANG TRUY VẤN API';
  resultState.classList.remove('active');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch('/v1/predictions', {
      method: 'POST',
      headers: {'content-type': 'application/json', 'x-api-key': apiKey},
      body: JSON.stringify({subscriber_key, as_of_date}),
      signal: controller.signal
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(explainHttpError(response, data));
    renderResult(data);
  } catch (error) {
    showError(error.name === 'AbortError' ? 'API phản hồi quá lâu. Hãy thử lại.' : error.message || 'Không thể kết nối API.');
  } finally {
    clearTimeout(timeout);
    submitButton.disabled = false;
    submitButton.firstElementChild.textContent = 'Chạy dự đoán';
  }
});

checkHealth();
