import os
import shutil
import hashlib
from PIL import Image
from collections import defaultdict
from tqdm import tqdm

RAW_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\raw"
CLEANED_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned"

# Mapping from raw folder names to standard class names
CLASS_MAPPING = {
    'bacterial_leaf_blight': 'bacterial_leaf_blight',
    'bacterialblight': 'bacterial_leaf_blight',
    'bacterial leaf blight': 'bacterial_leaf_blight',
    
    'bacterial_leaf_streak': 'bacterial_leaf_streak',
    'bacterial_panicle_blight': 'bacterial_panicle_blight',
    'blast': 'blast',
    
    'brown_spot': 'brown_spot',
    'brownspot': 'brown_spot',
    'brown spot': 'brown_spot',
    
    'dead_heart': 'dead_heart',
    'downy_mildew': 'downy_mildew',
    'hispa': 'hispa',
    'normal': 'normal',
    'tungro': 'tungro',
    
    # Adding Leaf Smut as a new 11th class since we have a lot of data
    'leafsmut': 'leaf_smut',
    'leaf smut': 'leaf_smut'
}

# Folders to ignore completely
IGNORE_FOLDERS = ['test_images']

def get_md5(image_path):
    hash_md5 = hashlib.md5()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def clean_data():
    if not os.path.exists(CLEANED_DIR):
        os.makedirs(CLEANED_DIR)

    stats = {
        'total_scanned': 0,
        'corrupted': 0,
        'duplicates': 0,
        'ignored_folder': 0,
        'valid': 0
    }
    
    class_counts = defaultdict(int)
    seen_hashes = set()
    
    # Pre-calculate total files for progress bar
    print("Đang đếm tổng số file...")
    all_files = []
    for root, dirs, files in os.walk(RAW_DIR):
        folder_name = os.path.basename(root).lower()
        if folder_name in IGNORE_FOLDERS:
            stats['ignored_folder'] += len(files)
            continue
            
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                all_files.append((root, file))

    print(f"Bắt đầu xử lý {len(all_files)} files...")
    
    for root, file in tqdm(all_files, desc="Đang làm sạch dữ liệu"):
        stats['total_scanned'] += 1
        folder_name = os.path.basename(root).lower()
        
        # Determine standard class name
        standard_class = CLASS_MAPPING.get(folder_name)
        if not standard_class:
            # Maybe it's a nested folder or unsupported class, skip or dump to "unknown"
            continue
            
        file_path = os.path.join(root, file)
        
        # 1. Check corruption
        try:
            with Image.open(file_path) as img:
                img.verify() # verify that it is, in fact, an image
        except Exception:
            stats['corrupted'] += 1
            continue
            
        # 2. Check duplicate
        file_hash = get_md5(file_path)
        if file_hash in seen_hashes:
            stats['duplicates'] += 1
            continue
        seen_hashes.add(file_hash)
        
        # 3. Create class folder if not exists
        class_dir = os.path.join(CLEANED_DIR, standard_class)
        if not os.path.exists(class_dir):
            os.makedirs(class_dir)
            
        # 4. Save standardized image
        try:
            with Image.open(file_path) as img:
                # Convert to RGB to standardize
                rgb_im = img.convert('RGB')
                save_path = os.path.join(class_dir, f"{file_hash}.jpg")
                rgb_im.save(save_path, 'JPEG', quality=95)
                stats['valid'] += 1
                class_counts[standard_class] += 1
        except Exception:
            stats['corrupted'] += 1
            continue

    print("\n" + "="*40)
    print("BÁO CÁO LÀM SẠCH DỮ LIỆU:")
    print("="*40)
    print(f"- Tổng số ảnh đã quét: {stats['total_scanned']}")
    print(f"- Ảnh bị bỏ qua (thư mục test/không hợp lệ): {stats['ignored_folder']}")
    print(f"- Ảnh bị lỗi (Corrupted): {stats['corrupted']}")
    print(f"- Ảnh bị trùng lặp (Duplicates): {stats['duplicates']}")
    print(f"- TỔNG SỐ ẢNH ĐẠT CHUẨN: {stats['valid']}")
    print("\nPhân bố dữ liệu sau làm sạch (Số lượng / Lớp):")
    for cls_name, count in sorted(class_counts.items()):
        print(f"  + {cls_name}: {count} ảnh")

if __name__ == "__main__":
    clean_data()
