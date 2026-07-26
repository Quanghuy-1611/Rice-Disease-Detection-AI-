import os
import glob
from PIL import Image, ImageEnhance
import random
from tqdm import tqdm
import shutil

RAW_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\raw"
CLEANED_DIR = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"

# Folder mapping (handles encoding gracefully by partial match)
folder_mapping = {
    "sheath_blight": "Sheath Blight",
    "hispa": "Rice Hispa",
    "southern_black_streaked_dwarf": "Lùn sọc đen",
    "whitebacked_planthopper": "rầy phấn trắng"
}

def find_actual_folder(target_part):
    for d in os.listdir(RAW_DIR):
        if target_part.lower() in d.lower():
            return os.path.join(RAW_DIR, d)
    # also try bytes matching if string is mangled
    for d in os.listdir(RAW_DIR):
        try:
            d_bytes = d.encode('cp1252', errors='ignore')
            if target_part.encode('utf-8', errors='ignore') in d_bytes:
                return os.path.join(RAW_DIR, d)
        except: pass
    return None

def augment_image(img):
    # Trả về danh sách các ảnh đã được augment
    aug_images = [img]
    
    # Lật trái phải
    img_flip = img.transpose(Image.FLIP_LEFT_RIGHT)
    aug_images.append(img_flip)
    
    # Xoay các góc
    for angle in [90, 180, 270, 45, -45]:
        aug_images.append(img.rotate(angle, expand=True))
        aug_images.append(img_flip.rotate(angle, expand=True))
        
    # Thay đổi độ sáng
    enhancer = ImageEnhance.Brightness(img)
    aug_images.append(enhancer.enhance(0.7))
    aug_images.append(enhancer.enhance(1.3))
    
    # Thay đổi độ tương phản
    enhancer_c = ImageEnhance.Contrast(img)
    aug_images.append(enhancer_c.enhance(0.7))
    aug_images.append(enhancer_c.enhance(1.3))
    
    return aug_images

def process():
    for class_name, raw_part in folder_mapping.items():
        actual_folder = find_actual_folder(raw_part)
        
        # Đặc biệt với lùn sọc đen và rầy phấn trắng, chữ tiếng việt có thể bị lỗi font 
        # nên ta duyệt trực tiếp các folder trong raw để tìm
        if not actual_folder:
            for d in os.listdir(RAW_DIR):
                if 's' in d.lower() and 'c' in d.lower() and 'den' in d.lower() and class_name == 'southern_black_streaked_dwarf':
                    actual_folder = os.path.join(RAW_DIR, d)
                if 'r' in d.lower() and 'y' in d.lower() and 'tr' in d.lower() and 'ng' in d.lower() and class_name == 'whitebacked_planthopper':
                    actual_folder = os.path.join(RAW_DIR, d)

        if not actual_folder or not os.path.exists(actual_folder):
            print(f"Không tìm thấy thư mục cho {class_name}")
            continue
            
        out_dir = os.path.join(CLEANED_DIR, class_name)
        os.makedirs(out_dir, exist_ok=True)
        
        # Đếm số file hiện có
        existing_files = glob.glob(os.path.join(out_dir, "*.jpg"))
        count = len(existing_files)
        
        raw_files = glob.glob(os.path.join(actual_folder, "*.*"))
        print(f"[{class_name}] Tìm thấy {len(raw_files)} ảnh gốc.")
        
        # Quyết định có cần Augment không (Dưới 50 ảnh thì Augment)
        needs_augment = len(raw_files) < 50
        
        added = 0
        for f in tqdm(raw_files, desc=class_name):
            try:
                img = Image.open(f).convert('RGB')
                if needs_augment:
                    # Augment thành ~20 ảnh
                    augs = augment_image(img)
                    for a_img in augs:
                        count += 1
                        added += 1
                        a_img_resized = a_img.resize((224, 224), Image.Resampling.LANCZOS)
                        a_img_resized.save(os.path.join(out_dir, f"{class_name}_{count:04d}.jpg"), 'JPEG', quality=95)
                else:
                    # Chỉ resize
                    count += 1
                    added += 1
                    img_resized = img.resize((224, 224), Image.Resampling.LANCZOS)
                    img_resized.save(os.path.join(out_dir, f"{class_name}_{count:04d}.jpg"), 'JPEG', quality=95)
            except Exception as e:
                pass
                
        print(f"[{class_name}] Đã thêm {added} ảnh vào cleaned_v4.")

if __name__ == "__main__":
    import sys
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    process()
    print("\n[SUCCESS] Hoàn tất nạp dữ liệu!")
