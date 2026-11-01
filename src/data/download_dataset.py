"""
Module tải và xác thực tập dữ liệu Customer Churn từ nguồn Kaggle chính thống.
"""
import os
import sys
import urllib.request
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "raw")
TRAIN_URL = "https://raw.githubusercontent.com/faisalghifari17/customer-churn-prediction/main/customer_churn_dataset-training-master.csv"
TEST_URL = "https://raw.githubusercontent.com/faisalghifari17/customer-churn-prediction/main/customer_churn_dataset-testing-master.csv"

TRAIN_FILE = os.path.join(RAW_DATA_DIR, "customer_churn_dataset-training-master.csv")
TEST_FILE = os.path.join(RAW_DATA_DIR, "customer_churn_dataset-testing-master.csv")


import hashlib
import json
import time

EXPECTED_HASHES = {
    "customer_churn_dataset-training-master.csv": "a41be7b96fb85110521bf03d1530879e9ca94b9f5de19866757f6d184300fff7",
    "customer_churn_dataset-testing-master.csv": "330af932f2dc1cae917f3bd0fb29395c4021319dd906189b7dc257d0ad58a617"
}


def ensure_directory(directory: str):
    """Tạo thư mục nếu chưa tồn tại."""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def compute_sha256(file_path: str) -> str:
    """Tính toán mã băm SHA256 của tệp tin."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def download_file_with_progress(url: str, output_path: str):
    """Tải tệp tin với thông báo tiến trình."""
    print(f"[*] Bắt đầu tải tệp từ: {url}")
    print(f"[*] Lưu vào: {output_path}")

    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded * 100 / total_size
            if block_num % 1000 == 0 or downloaded >= total_size:
                print(f"    - Tiến trình: {percent:.1f}% ({downloaded / (1024 * 1024):.1f}MB / {total_size / (1024 * 1024):.1f}MB)")

    urllib.request.urlretrieve(url, output_path, reporthook=reporthook)
    print(f"[+] Tải thành công: {output_path} ({os.path.getsize(output_path) / (1024*1024):.2f} MB)")


def verify_dataset(file_path: str, is_train: bool = True) -> bool:
    """Kiểm tra cấu trúc, tính toàn vẹn SHA256 của tệp CSV."""
    if not os.path.exists(file_path):
        print(f"[-] Lỗi: Không tìm thấy tệp {file_path}")
        return False

    fname = os.path.basename(file_path)
    file_hash = compute_sha256(file_path)
    expected_hash = EXPECTED_HASHES.get(fname)

    print(f"\n[*] Kiểm tra tệp: {fname}")
    print(f"    - SHA256: {file_hash}")
    if expected_hash and file_hash != expected_hash:
        print(f"[-] Lỗi: SHA256 không khớp! Kỳ vọng: {expected_hash}")
        return False
    print(f"[+] SHA256 đạt chuẩn toàn vẹn dữ liệu.")

    df = pd.read_csv(file_path, nrows=10)
    print(f"    - Các cột nhận diện được ({len(df.columns)}): {list(df.columns)}")

    required_columns = [
        "CustomerID", "Age", "Gender", "Tenure", "Usage Frequency",
        "Support Calls", "Payment Delay", "Subscription Type",
        "Contract Length", "Total Spend", "Last Interaction"
    ]
    if is_train:
        required_columns.append("Churn")

    for col in required_columns:
        if col not in df.columns:
            print(f"[-] Lỗi: Thiếu cột bắt buộc '{col}' trong tệp {file_path}")
            return False

    print(f"[+] Tệp {fname} đạt chuẩn cấu trúc Kaggle.")
    return True


def save_provenance_metadata():
    """Ghi nhận siêu dữ liệu nguồn gốc và băm của tập dữ liệu."""
    meta = {
        "dataset_name": "Customer Churn Dataset",
        "canonical_source": "https://www.kaggle.com/datasets/muhammadshahidazeem/customer-churn-dataset",
        "mirrored_download_url": TRAIN_URL,
        "verified_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "files": {
            "train": {
                "filename": os.path.basename(TRAIN_FILE),
                "sha256": compute_sha256(TRAIN_FILE),
                "size_bytes": os.path.getsize(TRAIN_FILE)
            },
            "test": {
                "filename": os.path.basename(TEST_FILE),
                "sha256": compute_sha256(TEST_FILE),
                "size_bytes": os.path.getsize(TEST_FILE)
            }
        }
    }
    meta_path = os.path.join(RAW_DATA_DIR, "data_sources.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[+] Đã lưu thông tin kiểm định nguồn gốc tại: {meta_path}")


def fetch_all(force: bool = False):
    """Tải và xác thực cả hai tập train và test."""
    ensure_directory(RAW_DATA_DIR)

    if force or not os.path.exists(TRAIN_FILE) or os.path.getsize(TRAIN_FILE) < 1000000:
        download_file_with_progress(TRAIN_URL, TRAIN_FILE)
    else:
        print(f"[i] Tệp train đã tồn tại: {TRAIN_FILE} ({os.path.getsize(TRAIN_FILE)/(1024*1024):.2f} MB)")

    if force or not os.path.exists(TEST_FILE) or os.path.getsize(TEST_FILE) < 500000:
        download_file_with_progress(TEST_URL, TEST_FILE)
    else:
        print(f"[i] Tệp test đã tồn tại: {TEST_FILE} ({os.path.getsize(TEST_FILE)/(1024*1024):.2f} MB)")

    train_ok = verify_dataset(TRAIN_FILE, is_train=True)
    test_ok = verify_dataset(TEST_FILE, is_train=False)

    if train_ok and test_ok:
        df_full = pd.read_csv(TRAIN_FILE)
        churn_count = int(df_full["Churn"].sum()) if "Churn" in df_full.columns else 0
        total_rows = len(df_full)
        print("\n================== THỐNG KÊ TẬP DỮ LIỆU KAGGLE (440k) ==================")
        print(f"[*] Tổng số bản ghi huấn luyện: {total_rows:,} dòng")
        print(f"[*] Số lượng khách hàng rời bỏ (Churn=1): {churn_count:,} ({churn_count/total_rows*100:.2f}%)")
        print(f"[*] Số lượng khách hàng ở lại (Churn=0): {total_rows - churn_count:,} ({(total_rows - churn_count)/total_rows*100:.2f}%)")
        print(f"[*] Dung lượng bộ nhớ RAM xấp xỉ: {df_full.memory_usage().sum() / (1024*1024):.2f} MB")
        print("=========================================================================")
        save_provenance_metadata()
        print("[OK] Toàn bộ dữ liệu thực tế đã sẵn sàng cho MLOps Pipeline.")
        return True
    else:
        print("\n[FAIL] Dữ liệu tải về không hợp lệ!")
        return False


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    sys.exit(0 if fetch_all(force=force_flag) else 1)

