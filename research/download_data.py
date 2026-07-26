import os
import urllib.request
import zipfile
import hashlib
import subprocess

DATA_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\raw"

def download_uci_dataset():
    print("Đang tải dataset 1 (UCI Rice Leaf Diseases - 120 ảnh)...")
    url = "https://archive.ics.uci.edu/static/public/486/rice+leaf+diseases.zip"
    zip_path = os.path.join(DATA_DIR, "uci_rice.zip")
    
    if not os.path.exists(zip_path):
        try:
            urllib.request.urlretrieve(url, zip_path)
            print("Tải xong UCI Dataset. Đang giải nén...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(DATA_DIR, "uci_rice"))
            os.remove(zip_path)
        except Exception as e:
            print(f"Lỗi khi tải UCI dataset: {e}")
    else:
        print("Dataset UCI đã tồn tại.")

def download_kaggle_dataset():
    print("\nĐang thử tải dataset 2 (Kaggle Paddy Disease Classification - Hơn 10.000 ảnh)...")
    try:
        # Chạy lệnh kaggle CLI
        subprocess.run(["kaggle", "competitions", "download", "-c", "paddy-disease-classification", "-p", DATA_DIR], check=True)
        
        kaggle_zip = os.path.join(DATA_DIR, "paddy-disease-classification.zip")
        if os.path.exists(kaggle_zip):
            print("Tải xong Kaggle dataset. Đang giải nén...")
            with zipfile.ZipFile(kaggle_zip, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(DATA_DIR, "kaggle_paddy"))
            os.remove(kaggle_zip)
    except Exception as e:
        print("\n[LƯU Ý]: Không thể tự động tải dataset từ Kaggle.")
        print("Lý do: Tải từ Kaggle qua dòng lệnh yêu cầu phải có API Token (file 'kaggle.json').")
        print("Vui lòng tải thủ công file zip từ link Kaggle về thư mục:")
        print(f"  {DATA_DIR}")
        print("Sau đó giải nén ra nhé.")

def remove_duplicates(directory):
    print("\nBắt đầu quét và xóa các ảnh trùng lặp...")
    hashes = set()
    duplicates_removed = 0
    total_files = 0
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                total_files += 1
                filepath = os.path.join(root, filename)
                
                # Tính mã băm (MD5) của file để kiểm tra trùng lặp
                hasher = hashlib.md5()
                with open(filepath, 'rb') as f:
                    buf = f.read()
                    hasher.update(buf)
                file_hash = hasher.hexdigest()
                
                if file_hash in hashes:
                    os.remove(filepath)
                    duplicates_removed += 1
                else:
                    hashes.add(file_hash)
                    
    print(f"Hoàn thành! Đã quét {total_files} ảnh.")
    print(f"Đã xóa {duplicates_removed} ảnh bị trùng lặp. Giữ lại {total_files - duplicates_removed} ảnh duy nhất.")

if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    download_uci_dataset()
    download_kaggle_dataset()
    remove_duplicates(DATA_DIR)
