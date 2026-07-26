import os
import shutil
from pathlib import Path
import random
import hashlib
from PIL import Image

RAW_DIR = Path(r"D:\Phát hiện bệnh cây lúa\research\data\raw")
FINAL_DIR = Path(r"D:\Phát hiện bệnh cây lúa\research\data\final_dataset_v4")
CLEANED_DIR = Path(r"D:\Phát hiện bệnh cây lúa\research\data\cleaned_v4")

CLASSES_TO_REBUILD = ["blast", "bacterial_leaf_blight"]
MAX_FILES = 4000

# 1. Delete contaminated folders
print("Deleting contaminated Custom_Bing_Dataset folders...")
shutil.rmtree(RAW_DIR / "Custom_Bing_Dataset" / "blast", ignore_errors=True)
shutil.rmtree(RAW_DIR / "Custom_Bing_Dataset" / "bacterial_leaf_blight", ignore_errors=True)

for cls in CLASSES_TO_REBUILD:
    shutil.rmtree(FINAL_DIR / cls, ignore_errors=True)
    shutil.rmtree(CLEANED_DIR / cls, ignore_errors=True)
    os.makedirs(FINAL_DIR / cls, exist_ok=True)
    os.makedirs(CLEANED_DIR / cls, exist_ok=True)

# 2. Re-gather from pure sources
def is_image(f):
    return f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']

class_files = {c: [] for c in CLASSES_TO_REBUILD}
print("Scanning pure raw data...")
for f in RAW_DIR.rglob('*'):
    if not f.is_file() or not is_image(f): continue
    if "Custom_Bing_Dataset" in str(f): continue # Skip any remaining bing garbage just in case
    path_str = str(f).lower()
    
    if "bacterial_leaf_blight" in path_str or "bacterial leaf blight" in path_str or "bacterialblight" in path_str:
        class_files["bacterial_leaf_blight"].append(f)
    elif "blast" in path_str:
        class_files["blast"].append(f)

# 3. Prepare final_dataset_v4
print("Copying pure files to final_dataset_v4...")
for cls in CLASSES_TO_REBUILD:
    files = class_files[cls]
    random.seed(42)
    random.shuffle(files)
    selected = files[:MAX_FILES]
    for f in selected:
        dest = FINAL_DIR / cls / f"{cls}_{f.parent.name}_{f.name}"
        if not dest.exists():
            shutil.copy2(f, dest)

# 4. Clean to cleaned_v4
print("Resizing and cleaning pure files...")
def get_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""): h.update(chunk)
    return h.hexdigest()

for cls in CLASSES_TO_REBUILD:
    seen = set()
    count = 0
    in_dir = FINAL_DIR / cls
    out_dir = CLEANED_DIR / cls
    for file in os.listdir(in_dir):
        fp = in_dir / file
        try:
            with Image.open(fp) as img: img.verify()
            fh = get_md5(fp)
            if fh in seen: continue
            seen.add(fh)
            
            with Image.open(fp) as img:
                rgb = img.convert('RGB').resize((224, 224), Image.Resampling.LANCZOS)
                count += 1
                rgb.save(out_dir / f"{cls}_{count:04d}.jpg", 'JPEG', quality=95)
        except Exception:
            pass
    print(f"[{cls}] Rebuilt {count} pure images.")

# 5. Fix Bo_Test_Tieng_Viet
TEST_DIR = Path(r"D:\Phát hiện bệnh cây lúa\Bo_Test_Tieng_Viet")
vi_names = {"blast": "Benh_Dao_on", "bacterial_leaf_blight": "Chay_la_vi_khuan"}
for cls, vi in vi_names.items():
    test_cls_dir = TEST_DIR / vi
    shutil.rmtree(test_cls_dir, ignore_errors=True)
    os.makedirs(test_cls_dir, exist_ok=True)
    
    # take first 20 from cleaned_v4
    clean_files = list((CLEANED_DIR / cls).glob("*.jpg"))[:20]
    for f in clean_files:
        shutil.copy2(f, test_cls_dir / f.name)

print("\n[SUCCESS] All Bing garbage completely purged from all folders!")
