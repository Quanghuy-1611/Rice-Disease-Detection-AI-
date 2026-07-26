import os
from pathlib import Path
from collections import defaultdict

RAW_DIR = Path(r"D:\Phát hiện bệnh cây lúa\research\data\raw")

counts = defaultdict(int)
for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
    for f in RAW_DIR.rglob(ext):
        # group by the folder it's inside
        parent = f.parent.name
        counts[parent] += 1
        
    for f in RAW_DIR.rglob(ext.upper()):
        parent = f.parent.name
        counts[parent] += 1

print("Image counts by parent folder:")
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    print(f"{k}: {v}")
