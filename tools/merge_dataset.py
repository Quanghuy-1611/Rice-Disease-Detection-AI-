import os
import shutil

def merge_data():
    raw_base = r"D:\Phát hiện bệnh cây lúa\research\data\raw\train\train"
    clean_base = r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4"
    
    # Bản đồ map thư mục thô (Raw) sang thư mục sạch (Cleaned)
    mapping = {
        "Brown Plant Hopper": "brown_planthopper",
        "Golden Apple Snail": "golden_apple_snail",
        "Rice Leaf Roller": "leaf_roller",
        "Rice Stem Borer Adult": "stem_borer",
        "Rice Stem Borer Larva": "stem_borer"
    }
    
    total_copied = 0
    
    for raw_folder, clean_folder in mapping.items():
        raw_dir = os.path.join(raw_base, raw_folder)
        clean_dir = os.path.join(clean_base, clean_folder)
        
        if not os.path.exists(raw_dir):
            print(f"Skipping {raw_folder} - Not found!")
            continue
            
        if not os.path.exists(clean_dir):
            os.makedirs(clean_dir)
            
        files = os.listdir(raw_dir)
        count = 0
        
        # Đếm số thứ tự cao nhất hiện có trong clean_folder để đặt tên tiếp theo
        existing_files = [f for f in os.listdir(clean_dir) if f.startswith(clean_folder)]
        start_idx = len(existing_files) + 1
        
        print(f"Merging {len(files)} files from {raw_folder} to {clean_folder}...")
        
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                src = os.path.join(raw_dir, f)
                new_name = f"{clean_folder}_{start_idx:04d}.jpg"
                dst = os.path.join(clean_dir, new_name)
                
                shutil.copy2(src, dst)
                start_idx += 1
                count += 1
                total_copied += 1
                
        print(f"  -> Copied {count} files.")
        
    print(f"\n[DONE] Successfully merged {total_copied} raw images into cleaned_v4!")

if __name__ == "__main__":
    merge_data()
