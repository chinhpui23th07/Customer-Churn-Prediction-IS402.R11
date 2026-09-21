import os
import requests

PAPERS = {
    "Kreuzberger_2022_MLOps_Architecture_Review.pdf": "https://arxiv.org/pdf/2205.02302",
    "Rabanser_2019_Failing_Loudly_Dataset_Shift_Detection.pdf": "https://arxiv.org/pdf/1910.10107",
    "Feature_Store_Survey_Architectures.pdf": "https://arxiv.org/pdf/2203.05315",
    "Kumar_Telecom_Churn_Prediction_Survey.pdf": "https://arxiv.org/pdf/2103.01853"
}

def download_papers():
    dest_dir = os.path.join("docs", "research", "papers")
    os.makedirs(dest_dir, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,application/pdf,*/*;q=0.8'
    }
    
    for filename, url in PAPERS.items():
        filepath = os.path.join(dest_dir, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 50000:
            print(f"Already exists: {filename} ({os.path.getsize(filepath)} bytes)")
            continue
        print(f"Downloading {filename} from {url}...")
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(resp.content)
                print(f"Successfully downloaded {filename} ({os.path.getsize(filepath)} bytes)")
            else:
                print(f"Failed {filename}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"Error downloading {filename}: {e}")

if __name__ == "__main__":
    download_papers()
