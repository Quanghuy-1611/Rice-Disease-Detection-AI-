import os
from pathlib import Path
from collections import defaultdict

RAW_DIR = Path(r"D:\Phát hiện bệnh cây lúa\research\data\raw")

# 18 classes
CLASSES = [
    "bacterial_leaf_blight", "bacterial_leaf_streak", "bacterial_panicle_blight", 
    "blast", "brown_spot", "dead_heart", "downy_mildew", "hispa", "normal", 
    "tungro", "leaf_smut", "weeds", "golden_apple_snail",
    "stem_borer", "leaf_roller", "brown_planthopper", "whitebacked_planthopper", "southern_black_streaked_dwarf"
]

class_counts = {c: 0 for c in CLASSES}

def is_image(f):
    return f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']

for f in RAW_DIR.rglob('*'):
    if not f.is_file() or not is_image(f):
        continue
    
    path_str = str(f).lower()
    
    # 1. Stem borer
    if "stem borer" in path_str or "stem_borer" in path_str: class_counts["stem_borer"] += 1
    # 2. Leaf roller / Skipper
    elif "leaf roller" in path_str or "skipper" in path_str or "leaf_roller" in path_str: class_counts["leaf_roller"] += 1
    # 3. Brown planthopper
    elif "brown plant hopper" in path_str or "brown_planthopper" in path_str: class_counts["brown_planthopper"] += 1
    # 4. Whitebacked planthopper
    elif "whitebacked" in path_str or "white_backed" in path_str: class_counts["whitebacked_planthopper"] += 1
    # 5. Southern black streaked dwarf
    elif "srbsdv" in path_str or "dwarf" in path_str or "southern_black" in path_str: class_counts["southern_black_streaked_dwarf"] += 1
    # 6. Weeds
    elif "weed" in path_str: class_counts["weeds"] += 1
    # 7. Golden Apple Snail
    elif "snail" in path_str: class_counts["golden_apple_snail"] += 1
    # 8. Leaf smut
    elif "smut" in path_str: class_counts["leaf_smut"] += 1
    # 9. Brown spot
    elif "brown spot" in path_str or "brownspot" in path_str or "brown_spot" in path_str: class_counts["brown_spot"] += 1
    # 10. Bacterial leaf blight
    elif "bacterial_leaf_blight" in path_str or "bacterial leaf blight" in path_str or "bacterialblight" in path_str: class_counts["bacterial_leaf_blight"] += 1
    # 11. Bacterial leaf streak
    elif "streak" in path_str: class_counts["bacterial_leaf_streak"] += 1
    # 12. Bacterial panicle blight
    elif "panicle" in path_str: class_counts["bacterial_panicle_blight"] += 1
    # 13. Blast
    elif "blast" in path_str: class_counts["blast"] += 1
    # 14. Dead heart
    elif "dead_heart" in path_str or "dead heart" in path_str: class_counts["dead_heart"] += 1
    # 15. Downy mildew
    elif "downy" in path_str: class_counts["downy_mildew"] += 1
    # 16. Hispa
    elif "hispa" in path_str: class_counts["hispa"] += 1
    # 17. Tungro
    elif "tungro" in path_str: class_counts["tungro"] += 1
    # 18. Normal
    elif "normal" in path_str or "healthy" in path_str: class_counts["normal"] += 1

print("Total images per 18 classes based on raw directories:")
total = 0
for k, v in sorted(class_counts.items(), key=lambda x: -x[1]):
    print(f"{k}: {v}")
    total += v
print(f"Grand Total Matched: {total}")
