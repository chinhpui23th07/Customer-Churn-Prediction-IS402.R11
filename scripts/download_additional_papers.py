import os
import requests

ADDITIONAL_PAPERS = {
    "Lundberg_2017_SHAP_Unified_Model_Interpretation.pdf": "https://arxiv.org/pdf/1705.07874",
    "Explainable_Customer_Churn_Prediction_XAI.pdf": "https://arxiv.org/pdf/2307.03925",
    "Cost_Sensitive_Customer_Churn_Prediction.pdf": "https://arxiv.org/pdf/2004.09575",
    "Continual_Learning_and_Dataset_Drift_Survey.pdf": "https://arxiv.org/pdf/2204.06201"
}

def download_additional_papers():
    dest_dir = os.path.join("docs", "research", "papers")
    os.makedirs(dest_dir, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    for filename, url in ADDITIONAL_PAPERS.items():
        filepath = os.path.join(dest_dir, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 50000:
            print(f"Already exists: {filename} ({os.path.getsize(filepath)} bytes)")
            continue
        print(f"Downloading {filename} from {url}...")
        try:
            resp = requests.get(url, headers=headers, timeout=40)
            if resp.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(resp.content)
                print(f"Successfully downloaded {filename} ({os.path.getsize(filepath)} bytes)")
            else:
                print(f"Failed {filename}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"Error downloading {filename}: {e}")

if __name__ == "__main__":
    download_additional_papers()
