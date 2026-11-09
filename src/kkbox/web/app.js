const form = document.getElementById('prediction-form');
const errorBox = document.getElementById('form-error');
const submitButton = document.getElementById('submit-button');
const statusBox = document.getElementById('system-status');
const statusText = document.getElementById('system-status-text');
const resultState = document.getElementById('result-state');
const riskLabels = {low: 'RỦI RO THẤP', medium: 'RỦI RO TRUNG BÌNH', high: 'RỦI RO CAO'};
const maxUint64 = 18446744073709551615n;
const featureLabels = {
  txn_count_30d: 'Số giao dịch 30 ngày', paid_amount_30d: 'Số tiền thanh toán 30 ngày',
  cancel_count_90d: 'Số lần hủy 90 ngày', days_since_last_txn: 'Ngày từ giao dịch cuối',
  last_auto_renew: 'Tự gia hạn gần nhất (0/1)', days_until_expiry: 'Ngày đến hạn thuê bao',
  active_days_30d: 'Số ngày nghe 30 ngày', listening_secs_30d: 'Giây nghe 30 ngày',
  days_since_last_listen: 'Ngày từ lần nghe cuối', registration_tenure_days: 'Ngày từ khi đăng ký',
  has_txn_history: 'Có lịch sử giao dịch (0/1)', has_listening_history: 'Có lịch sử nghe (0/1)'
};
const featureNames = Object.keys(featureLabels);
const modes = {manual: document.getElementById('manual-form'), batch: document.getElementById('batch-form'), lookup: form};
const featureOutput = document.getElementById('feature-output');
const batchOutput = document.getElementById('batch-output');

for (const name of featureNames) {
  const field = document.createElement('div');
  field.className = 'field';
  const label = document.createElement('label');
  label.htmlFor = 'feature-' + name;
  label.textContent = featureLabels[name];
  const input = document.createElement('input');
  input.id = label.htmlFor;
  input.type = 'number';
  input.step = 'any';
  input.placeholder = name;
  field.append(label, input);
  document.getElementById('manual-fields').append(field);
}

document.querySelectorAll('.mode-tabs [role="tab"]').forEach(tab => tab.addEventListener('click', () => {
  for (const [mode, panel] of Object.entries(modes)) panel.hidden = mode !== tab.dataset.mode;
  document.querySelectorAll('.mode-tabs [role="tab"]').forEach(item => item.setAttribute('aria-selected', String(item === tab)));
  clearError();
}));

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
  batchOutput.hidden = true;
  document.getElementById('score-ring').style.setProperty('--score', percent + '%');
  document.getElementById('score-value').textContent = percent.toFixed(1) + '%';
  document.getElementById('meter-fill').style.width = percent + '%';
  document.getElementById('prediction-label').textContent = data.prediction === 1 ? 'Có nguy cơ rời bỏ' : 'Dự đoán tiếp tục';
  const badge = document.getElementById('risk-badge');
  badge.className = 'risk-badge ' + data.risk_level;
  badge.textContent = riskLabels[data.risk_level];
  document.getElementById('result-cutoff').textContent = data.as_of_date || 'Kịch bản giả định';
  document.getElementById('result-model').textContent = String(data.model_version);
  document.getElementById('result-feature').textContent = String(data.feature_version);
  document.getElementById('result-mode').textContent = data.prediction_mode === 'manual_scenario' ? 'Nhập feature' : 'Phát lại lịch sử';
  document.getElementById('result-disclaimer').textContent = data.prediction_mode === 'manual_scenario'
    ? 'Kịch bản nhập tay có thể thiếu feature và không đại diện cho một khách hàng thật trong dataset.'
    : 'Xác suất của mô hình tại cutoff đã chọn; không phải nhãn churn thật hoặc cam kết khách hàng sẽ rời bỏ.';
  resultState.textContent = 'DỰ ĐOÁN HOÀN TẤT';
  resultState.classList.add('active');
}

async function postJson(path, body, apiKey, timeoutMs = 30000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      method: 'POST', headers: {'content-type': 'application/json', 'x-api-key': apiKey},
      body: JSON.stringify(body), signal: controller.signal
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(explainHttpError(response, data));
    return data;
  } finally { clearTimeout(timeout); }
}

function addDataTable(target, rows, headings) {
  const table = document.createElement('table');
  const head = table.createTHead().insertRow();
  for (const title of headings) { const cell = document.createElement('th'); cell.textContent = title; head.append(cell); }
  const body = table.createTBody();
  for (const row of rows) {
    const line = body.insertRow();
    for (const value of row) { const cell = line.insertCell(); cell.textContent = String(value ?? '—'); }
  }
  target.replaceChildren(table);
  target.hidden = false;
}

function apiKeyValue() { return document.getElementById('api-key').value; }

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
  const apiKey = apiKeyValue();
  if (!validSubscriberKey(subscriber_key)) return showError('Subscriber key phải là chuỗi số thập phân chuẩn trong phạm vi uint64.');
  if (!['2017-01-31', '2017-02-28'].includes(as_of_date)) return showError('Ngày chốt không được hỗ trợ.');
  if (!apiKey) return showError('Hãy nhập mã truy cập demo.');
  submitButton.disabled = true;
  submitButton.firstElementChild.textContent = 'Đang tính toán...';
  resultState.textContent = 'ĐANG TRUY VẤN API';
  resultState.classList.remove('active');
  try {
    const payload = {subscriber_key, as_of_date};
    const features = await postJson('/v1/features', payload, apiKey);
    const prediction = await postJson('/v1/predictions', payload, apiKey);
    renderResult(prediction);
    addDataTable(featureOutput, Object.entries(features.features).map(([name, value]) => [featureLabels[name], value]), ['Feature từ Feast', 'Giá trị']);
    featureOutput.prepend(Object.assign(document.createElement('p'), {textContent: `Đã tra ${featureNames.length} feature · thiếu ${features.missing_count} giá trị` }));
  } catch (error) {
    showError(error.name === 'AbortError' ? 'API phản hồi quá lâu. Hãy thử lại.' : error.message || 'Không thể kết nối API.');
  } finally {
    submitButton.disabled = false;
    submitButton.firstElementChild.textContent = 'Chạy dự đoán';
  }
});

document.getElementById('manual-form').addEventListener('submit', async event => {
  event.preventDefault(); clearError(); featureOutput.hidden = true;
  const apiKey = apiKeyValue();
  if (!apiKey) return showError('Hãy nhập mã truy cập demo.');
  const features = {};
  for (const name of featureNames) {
    const value = document.getElementById('feature-' + name).value.trim();
    features[name] = value === '' ? null : Number(value);
    if (value !== '' && !Number.isFinite(features[name])) return showError('Feature ' + name + ' phải là số hữu hạn.');
  }
  if (Object.values(features).every(value => value === null)) return showError('Hãy nhập ít nhất một feature.');
  const button = event.currentTarget.querySelector('button[type="submit"]'); button.disabled = true;
  try { renderResult(await postJson('/v1/predictions/manual', {features}, apiKey)); }
  catch (error) { showError(error.message || 'Không thể kết nối API.'); }
  finally { button.disabled = false; }
});

function parseBatchCsv(text) {
  const lines = text.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
  if (lines.shift()?.trim() !== 'subscriber_key,as_of_date') throw new Error('CSV phải bắt đầu bằng subscriber_key,as_of_date.');
  if (!lines.length || lines.length > 100) throw new Error('CSV cần từ 1 đến 100 dòng dữ liệu.');
  return lines.map((line, index) => {
    const cells = line.split(',').map(value => value.trim().replace(/^"([^"]*)"$/, '$1'));
    if (cells.length !== 2 || !validSubscriberKey(cells[0]) || !['2017-01-31', '2017-02-28'].includes(cells[1]))
      throw new Error('Dòng ' + (index + 2) + ' không hợp lệ.');
    return {subscriber_key: cells[0], as_of_date: cells[1]};
  });
}

document.getElementById('batch-form').addEventListener('submit', async event => {
  event.preventDefault(); clearError(); featureOutput.hidden = true;
  const apiKey = apiKeyValue();
  const file = document.getElementById('batch-file').files[0];
  if (!apiKey) return showError('Hãy nhập mã truy cập demo.');
  if (!file) return showError('Hãy chọn tệp CSV.');
  if (file.size > 256 * 1024) return showError('CSV vượt giới hạn 256 KiB.');
  const button = event.currentTarget.querySelector('button[type="submit"]'); button.disabled = true;
  try {
    const items = parseBatchCsv(await file.text());
    const data = await postJson('/v1/predictions/batch', {items}, apiKey, 120000);
    document.getElementById('result-empty').hidden = true;
    document.getElementById('result-data').hidden = true;
    addDataTable(batchOutput, data.results.map(item => [item.row, item.subscriber_key, item.as_of_date,
      item.result ? (item.result.churn_probability * 100).toFixed(1) + '%' : '—',
      item.result ? (item.result.prediction === 1 ? 'Rời bỏ' : 'Tiếp tục') : item.error,
      item.result?.model_version || '—']), ['Dòng', 'Subscriber key', 'Ngày chốt', 'Xác suất', 'Kết quả', 'Model']);
    batchOutput.prepend(Object.assign(document.createElement('p'), {textContent: `Tổng ${data.total} · thành công ${data.succeeded} · thiếu snapshot ${data.failed}`}));
    resultState.textContent = 'BATCH HOÀN TẤT'; resultState.classList.add('active');
  } catch (error) { showError(error.message || 'Không thể xử lý CSV.'); }
  finally { button.disabled = false; }
});

checkHealth();
