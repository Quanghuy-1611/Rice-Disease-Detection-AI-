import os
import shutil
import random
from pathlib import Path
from collections import defaultdict

RAW_DIR = Path(r"D:\Phát hiện bệnh cây lúa\research\data\raw")
OUT_DIR = Path(r"D:\Phát hiện bệnh cây lúa\research\data\final_dataset_v4")

# 19 classes
CLASSES = [
    "bacterial_leaf_blight", "bacterial_leaf_streak", "bacterial_panicle_blight", 
    "blast", "brown_spot", "dead_heart", "downy_mildew", "hispa", "normal", 
    "tungro", "leaf_smut", "weeds", "golden_apple_snail",
    "stem_borer", "leaf_roller", "brown_planthopper", "whitebacked_planthopper", 
    "southern_black_streaked_dwarf", "sheath_blight"
]

# Create output directories
for cls in CLASSES:
    os.makedirs(OUT_DIR / cls, exist_ok=True)

def is_image(f):
    return f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']

# 1. Gather files per class
class_files = defaultdict(list)

print("Đang quét toàn bộ file trong data/raw...")
for f in RAW_DIR.rglob('*'):
    if not f.is_file() or not is_image(f):
        continue
    
    path_str = str(f).lower()
    
    # 1. Stem borer
    if "stem borer" in path_str or "stem_borer" in path_str: class_files["stem_borer"].append(f)
    # 2. Leaf roller / Skipper
    elif "leaf roller" in path_str or "skipper" in path_str or "leaf_roller" in path_str: class_files["leaf_roller"].append(f)
    # 3. Brown planthopper
    elif "brown plant hopper" in path_str or "brown_planthopper" in path_str: class_files["brown_planthopper"].append(f)
    # 4. Whitebacked planthopper
    elif "whitebacked" in path_str or "white_backed" in path_str: class_files["whitebacked_planthopper"].append(f)
    # 5. Southern black streaked dwarf
    elif "srbsdv" in path_str or "dwarf" in path_str or "southern_black" in path_str: class_files["southern_black_streaked_dwarf"].append(f)
    # 6. Weeds
    elif "weed" in path_str: class_files["weeds"].append(f)
    # 7. Golden Apple Snail
    elif "snail" in path_str: class_files["golden_apple_snail"].append(f)
    # 8. Leaf smut
    elif "smut" in path_str: class_files["leaf_smut"].append(f)
    # 9. Sheath Blight (NEW)
    elif "sheath" in path_str or "kho_van" in path_str: class_files["sheath_blight"].append(f)
    # 10. Brown spot
    elif "brown spot" in path_str or "brownspot" in path_str or "brown_spot" in path_str: class_files["brown_spot"].append(f)
    # 11. Bacterial leaf blight
    elif "bacterial_leaf_blight" in path_str or "bacterial leaf blight" in path_str or "bacterialblight" in path_str: class_files["bacterial_leaf_blight"].append(f)
    # 12. Bacterial leaf streak
    elif "streak" in path_str: class_files["bacterial_leaf_streak"].append(f)
    # 13. Bacterial panicle blight
    elif "panicle" in path_str: class_files["bacterial_panicle_blight"].append(f)
    # 14. Blast
    elif "blast" in path_str: class_files["blast"].append(f)
    # 15. Dead heart
    elif "dead_heart" in path_str or "dead heart" in path_str: class_files["dead_heart"].append(f)
    # 16. Downy mildew
    elif "downy" in path_str: class_files["downy_mildew"].append(f)
    # 17. Hispa
    elif "hispa" in path_str: class_files["hispa"].append(f)
    # 18. Tungro
    elif "tungro" in path_str: class_files["tungro"].append(f)
    # 19. Normal
    elif "normal" in path_str or "healthy" in path_str: class_files["normal"].append(f)

# 2. Limit and Copy
MAX_FILES_PER_CLASS = 4000

print(f"Đang chuẩn bị dataset (Limit: {MAX_FILES_PER_CLASS} ảnh/class)...")
for cls in CLASSES:
    files = class_files.get(cls, [])
    
    # Shuffle files to get random samples if it exceeds limit
    random.seed(42)
    random.shuffle(files)
    
    selected_files = files[:MAX_FILES_PER_CLASS]
    
    count = 0
    for f in selected_files:
        dest_path = OUT_DIR / cls / f"{cls}_{f.parent.name}_{f.name}"
        if not dest_path.exists():
            try:
                shutil.copy2(f, dest_path)
                count += 1
            except Exception as e:
                pass
    print(f"[{cls}]: Sao chép {count}/{len(selected_files)} file.")

print("Hoàn tất chuẩn bị Dataset V4!")
