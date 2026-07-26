import os
from transformers import pipeline
from PIL import Image
from tqdm import tqdm
import glob

# Khởi tạo mô hình CLIP (hỗ trợ zero-shot classification)
# Mô hình này rất nhẹ, tự động tải xuống và chạy trên CPU khá nhanh
print("Đang tải mô hình AI CLIP để lọc ảnh rác...")
classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

# Các nhãn để CLIP phân loại
# Nếu ảnh giống với nhãn rác hơn nhãn chuẩn, ta sẽ xóa nó.
labels = [
    "a photo of a rice plant disease, rice leaf, insect, bug, snail, weed, or agriculture",
    "a photo of a person, dog, cat, map, meme, text, indoor object, or human face"
]

def scan_and_delete(target_dir):
    deleted_count = 0
    total_scanned = 0
    
    # Lấy danh sách tất cả các ảnh .jpg trong tất cả các thư mục con
    all_images = glob.glob(os.path.join(target_dir, "*", "*.jpg"))
    print(f"Bắt đầu quét {len(all_images)} ảnh trong thư mục {target_dir}...")
    
    for img_path in tqdm(all_images):
        try:
            total_scanned += 1
            # Mở ảnh
            img = Image.open(img_path)
            
            # Phân loại
            res = classifier(img, candidate_labels=labels)
            
            # Kết quả là một list dict: [{'score': 0.99, 'label': '...'}, {'score': 0.01, 'label': '...'}]
            top_label = res[0]['label']
            
            if "person, dog, cat, map" in top_label:
                # Đây là ảnh rác!
                os.remove(img_path)
                deleted_count += 1
        except Exception as e:
            # Lỗi khi đọc ảnh (ảnh hỏng) thì cũng xóa luôn
            try:
                os.remove(img_path)
                deleted_count += 1
            except:
                pass
                
    return total_scanned, deleted_count

if __name__ == "__main__":
    dirs_to_clean = [
        r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4",
        r"D:\Phát hiện bệnh cây lúa\Bo_Test_Tieng_Viet"
    ]
    
    total_deleted = 0
    for d in dirs_to_clean:
        scanned, deleted = scan_and_delete(d)
        total_deleted += deleted
        print(f"-> Đã quét {scanned} ảnh trong {d}, xóa {deleted} ảnh rác.")
        
    print(f"\n[HOÀN TẤT] Tổng cộng đã tiêu diệt {total_deleted} tấm ảnh rác khỏi hệ thống!")
