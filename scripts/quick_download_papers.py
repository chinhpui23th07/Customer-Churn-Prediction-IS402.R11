import os
import requests

papers_to_try = {
    "XAI_Explainability_in_Machine_Learning_Survey.pdf": "https://arxiv.org/pdf/2006.00093",
    "Data_Drift_and_ML_Monitoring_Practices.pdf": "https://arxiv.org/pdf/2007.06299"
}

dest_dir = os.path.join("docs", "research", "papers")
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/pdf,*/*'
}

for name, url in papers_to_try.items():
    dest = os.path.join(dest_dir, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 50000:
        continue
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            with open(dest, "wb") as f:
                f.write(r.content)
            print(f"Downloaded: {name} ({os.path.getsize(dest)} bytes)")
    except Exception as e:
        print(f"Skipped {name}: {e}")
