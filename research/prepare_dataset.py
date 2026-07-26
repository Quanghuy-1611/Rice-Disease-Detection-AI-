import os
import shutil
import random
from pathlib import Path

RAW_DIR = Path("D:/Phát hiện bệnh cây lúa/research/data/raw")
OUT_DIR = Path("D:/Phát hiện bệnh cây lúa/research/data/final_dataset")

# The 14 classes
CLASSES = [
    "bacterial_leaf_blight", "bacterial_leaf_streak", "bacterial_panicle_blight", 
    "blast", "brown_spot", "dead_heart", "downy_mildew", "hispa", "normal", 
    "tungro", "leaf_smut", "insects", "weeds", "golden_apple_snail"
]

# Create output directories
for cls in CLASSES:
    os.makedirs(OUT_DIR / cls, exist_ok=True)

def copy_files(src_dir, dest_class, max_files=2000):
    if not os.path.exists(src_dir): return
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
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
    # Print statement removed to prevent UnicodeEncodeError in Windows console

# 1. Original 11 classes (copying from their raw folders if they exist, or cleaned)
ORIGINAL_CLASSES = CLASSES[:11]
for cls in ORIGINAL_CLASSES:
    # copy from old raw folder if it matches
    copy_files(RAW_DIR / cls, cls, 2000)

# 2. Golden Apple Snail
copy_files(RAW_DIR / "train" / "train" / "Golden Apple Snail", "golden_apple_snail", 1000)
copy_files(RAW_DIR / "train" / "train" / "Golden Apple Snail Egg", "golden_apple_snail", 1000)
copy_files(RAW_DIR / "valid" / "valid" / "Golden Apple Snail", "golden_apple_snail", 500)
copy_files(RAW_DIR / "golden-apple-snail", "golden_apple_snail", 1000)

# 3. Insects (combine everything else from train/train)
INSECT_DIRS = [
    "Beetle", "Brown Plant Hopper", "Grass Hopper", "Paddy Stem Maggot", 
    "Rice Gall Midge", "Rice Leaf Caterpillar", "Rice Leaf Hopper", 
    "Rice Leaf Roller", "Rice Skipper", "Rice Stem Borer Adult", 
    "Rice Stem Borer Larva", "Rice Water Weevil", "Thrips"
]
for idir in INSECT_DIRS:
    copy_files(RAW_DIR / "train" / "train" / idir, "insects", 300) # 300 each to avoid imbalanced huge class

# 4. Weeds
copy_files(RAW_DIR / "Crop-and-weed", "weeds", 500)
copy_files(RAW_DIR / "Weed-Detection-usign-Yolo", "weeds", 500)

# Also check RicePest-30 for more insects
copy_files(RAW_DIR / "RicePest-30", "insects", 1000)

print("Dataset preparation complete!")
