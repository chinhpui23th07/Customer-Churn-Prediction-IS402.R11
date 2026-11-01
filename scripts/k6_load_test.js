import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom SLO Metrics (inspired by grafana/k6 24k+ stars)
export const errorRate = new Rate('slo_error_rate');
export const predictLatency = new Trend('slo_predict_duration');

// Test Configuration & Strict Cloud SLO Thresholds
export const options = {
  stages: [
    { duration: '3s', target: 10 },   // Warmup ramp to 10 VUs
    { duration: '10s', target: 25 },  // Sustained load test at 25 VUs
    { duration: '3s', target: 0 },    // Cooldown ramp down
  ],
  thresholds: {
    // SLO 1: Error rate strictly below 1.0%
    'http_req_failed': ['rate<0.01'],
    'slo_error_rate': ['rate<0.01'],
    // SLO 2: 95th percentile latency strictly below 150ms
    'http_req_duration': ['p(95)<150'],
    'slo_predict_duration': ['p(95)<150'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'mlops-churn-secret-2026';

const samplePayload = JSON.stringify({
  customer_id: 10452,
  age: 38.0,
  gender: 'Female',
  tenure: 12.0,
  usage_frequency: 18.0,
  support_calls: 2.0,
  payment_delay: 1.0,
  subscription_type: 'Standard',
  contract_length: 'Monthly',
  total_spend: 620.5,
  last_interaction: 8.0,
});

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
  'X-Requested-With': 'XMLHttpRequest',
};

export default function () {
  // 1. Health Probe Check
  const healthRes = http.get(`${BASE_URL}/health`);
  const healthOk = check(healthRes, {
    'health status is 200': (r) => r.status === 200,
  });
  errorRate.add(!healthOk);

  // 2. High-Throughput Customer Churn Prediction Inference
  const predictRes = http.post(`${BASE_URL}/predict`, samplePayload, { headers });
  const predictOk = check(predictRes, {
    'predict status is 200': (r) => r.status === 200,
    'predict returns churn_prediction': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body && body.churn_prediction !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  errorRate.add(!predictOk);
  predictLatency.add(predictRes.timings.duration);

  sleep(0.05); // Simulated realistic client pacing
}
