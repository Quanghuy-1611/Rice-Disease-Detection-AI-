import os
import hashlib
from PIL import Image
from collections import defaultdict
from tqdm import tqdm

IN_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\final_dataset_v3"
OUT_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v3"

def get_md5(image_path):
    hash_md5 = hashlib.md5()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def clean():
    os.makedirs(OUT_DIR, exist_ok=True)
    seen_hashes = set()
    
    # gather files
    all_files = []
    for cls in os.listdir(IN_DIR):
        cls_dir = os.path.join(IN_DIR, cls)
        if not os.path.isdir(cls_dir): continue
        for file in os.listdir(cls_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                all_files.append((cls, os.path.join(cls_dir, file)))
    
    class_counts = defaultdict(int)
    for cls, file_path in tqdm(all_files, desc="Cleaning Data"):
        # 1. verify
        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception:
            continue
            
        # 2. Duplicate check
        file_hash = get_md5(file_path)
        if file_hash in seen_hashes:
            continue
        seen_hashes.add(file_hash)
        
        # 3. resize, convert and save
        out_cls_dir = os.path.join(OUT_DIR, cls)
        os.makedirs(out_cls_dir, exist_ok=True)
        class_counts[cls] += 1
        
        try:
            with Image.open(file_path) as img:
                rgb_im = img.convert('RGB')
                rgb_im = rgb_im.resize((224, 224), Image.Resampling.LANCZOS)
                save_path = os.path.join(out_cls_dir, f"{cls}_{class_counts[cls]:04d}.jpg")
                rgb_im.save(save_path, 'JPEG', quality=95)
        except Exception:
            class_counts[cls] -= 1
            continue
            
if __name__ == "__main__":
    clean()
