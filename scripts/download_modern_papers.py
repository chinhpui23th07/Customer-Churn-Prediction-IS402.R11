import urllib.request
import ssl
import os

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

papers = [
    ("2408.16284", "Adaptive_Ensemble_Churn_Prediction_2024.pdf"),
    ("2412.11308", "XAI_to_MLOps_Concept_Drift_2024.pdf"),
    ("2507.08860", "Business_Aligned_Churn_Metrics_2025.pdf"),
    ("2510.11604", "Personalized_Retention_XAI_Churn_2025.pdf"),
    ("2512.11541", "Automated_MLOps_Retraining_Distribution_Shifts_2025.pdf"),
    ("2603.03341", "Ethical_XAI_Reusable_MLOps_Pipelines_2026.pdf")
]

os.makedirs("docs/research/papers", exist_ok=True)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for arxiv_id, fname in papers:
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    dest = os.path.join("docs", "research", "papers", fname)
    print(f"Downloading {arxiv_id} -> {dest}...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=60) as resp, open(dest, "wb") as f:
            content = resp.read()
            f.write(content)
        print(f"[+] Success: {fname} ({len(content)} bytes)")
    except Exception as e:
        print(f"[-] Error downloading {arxiv_id}: {e}")
