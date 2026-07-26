import os
import hashlib
from datasets import load_dataset
from tqdm import tqdm

DATA_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\raw\kaggle_paddy"
hashes = set()
duplicates = 0
saved = 0

def save_and_dedup(img, save_path):
    global duplicates, saved
    # Compute hash of the PIL Image
    hasher = hashlib.md5()
    hasher.update(img.tobytes())
    img_hash = hasher.hexdigest()
    
    if img_hash in hashes:
        duplicates += 1
    else:
        hashes.add(img_hash)
        img.save(save_path)
        saved += 1

print("Đang tải Paddy Disease Classification dataset từ Hugging Face...")
# Dataset này tương đương với bộ Kaggle
ds = load_dataset("anthony2261/paddy-disease-classification")

print("Đang lưu ảnh và lọc trùng lặp. Quá trình này có thể mất vài phút...")
for split in ds.keys():
    print(f"Xử lý tập: {split}")
    
    for i, item in enumerate(tqdm(ds[split])):
        img = item['image']
        label = item['label']
        
        # Get class name
        if isinstance(label, int):
            class_name = ds[split].features['label'].int2str(label)
        else:
            class_name = str(label)
            
        class_dir = os.path.join(DATA_DIR, split, class_name)
        os.makedirs(class_dir, exist_ok=True)
        
        save_path = os.path.join(class_dir, f"img_{i}.jpg")
        
        # Save image and dedup
        save_and_dedup(img, save_path)

print("\nHoàn tất tải 10.000+ ảnh!")
print(f"Tổng số ảnh tải về và giữ lại: {saved}")
print(f"Số ảnh trùng lặp đã bị xóa: {duplicates}")
