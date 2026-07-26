import os
import shutil
import random
from pathlib import Path

RAW_DIR = Path("D:/Phát hiện bệnh cây lúa/research/data/raw")
OUT_DIR = Path("D:/Phát hiện bệnh cây lúa/research/data/final_dataset_v3")

# The 18 classes
CLASSES = [
    "bacterial_leaf_blight", "bacterial_leaf_streak", "bacterial_panicle_blight", 
    "blast", "brown_spot", "dead_heart", "downy_mildew", "hispa", "normal", 
    "tungro", "leaf_smut", "weeds", "golden_apple_snail",
    "stem_borer", "leaf_roller", "brown_planthopper", "whitebacked_planthopper", "southern_black_streaked_dwarf"
]

# Create output directories
for cls in CLASSES:
    os.makedirs(OUT_DIR / cls, exist_ok=True)

def copy_files(src_dir, dest_class, max_files=2000):
    if not os.path.exists(src_dir): return
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
        files.extend(list(Path(src_dir).rglob(ext)))
        files.extend(list(Path(src_dir).rglob(ext.upper())))
    
    # Shuffle and limit
    random.seed(42)
    random.shuffle(files)
    files = files[:max_files]
    
    count = 0
    for f in files:
        dest_path = OUT_DIR / dest_class / f"{dest_class}_{f.parent.name}_{f.name}"
        if not dest_path.exists():
            try:
                shutil.copy2(f, dest_path)
                count += 1
            except:
                pass

# 1. Original 11 classes
ORIGINAL_CLASSES = CLASSES[:11]
for cls in ORIGINAL_CLASSES:
    copy_files(RAW_DIR / cls, cls, 2000)

# 2. Golden Apple Snail
copy_files(RAW_DIR / "train" / "train" / "Golden Apple Snail", "golden_apple_snail", 1000)
copy_files(RAW_DIR / "train" / "train" / "Golden Apple Snail Egg", "golden_apple_snail", 1000)
copy_files(RAW_DIR / "golden-apple-snail", "golden_apple_snail", 1000)

# 3. Weeds
copy_files(RAW_DIR / "Crop-and-weed", "weeds", 1000)
copy_files(RAW_DIR / "Weed-Detection-usign-Yolo", "weeds", 1000)

# 4. New 5 Classes
# 4.1. Stem Borer (Sâu đục thân)
copy_files(RAW_DIR / "train" / "train" / "Rice Stem Borer Adult", "stem_borer", 1000)
copy_files(RAW_DIR / "train" / "train" / "Rice Stem Borer Larva", "stem_borer", 1000)
copy_files(RAW_DIR / "valid" / "valid" / "Rice Stem Borer Adult", "stem_borer", 200)

# 4.2. Leaf Roller (Sâu cuốn lá)
copy_files(RAW_DIR / "train" / "train" / "Rice Leaf Roller", "leaf_roller", 1000)
copy_files(RAW_DIR / "train" / "train" / "Rice Skipper", "leaf_roller", 500) # Similar folding damage

# 4.3. Brown Planthopper (Rầy nâu)
copy_files(RAW_DIR / "train" / "train" / "Brown Plant Hopper", "brown_planthopper", 1000)
copy_files(RAW_DIR / "valid" / "valid" / "Brown Plant Hopper", "brown_planthopper", 500)

# 4.4. Whitebacked Planthopper (Rầy phấn trắng)
copy_files(RAW_DIR / "Custom_Bing_Dataset" / "Whitebacked_planthopper", "whitebacked_planthopper", 2000)

# 4.5. Southern Rice Black-Streaked Dwarf (Lùn sọc đen)
copy_files(RAW_DIR / "Custom_Bing_Dataset" / "SRBSDV", "southern_black_streaked_dwarf", 2000)

print("Dataset preparation complete for 18 classes!")
