from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path("research/dataset_11_curated")
OUT = Path("research/audit_11class_label_review")
SEED = 2026
SAMPLES = 24
COLS = 4
CELL_W, CELL_H = 260, 235
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

OUT.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()
for label_dir in sorted(path for path in ROOT.iterdir() if path.is_dir()):
    files = sorted(path for path in label_dir.iterdir() if path.suffix.lower() in EXTS)
    rng = random.Random(f"{SEED}:{label_dir.name}")
    chosen = rng.sample(files, min(SAMPLES, len(files)))
    rows = (len(chosen) + COLS - 1) // COLS
    canvas = Image.new("RGB", (COLS * CELL_W, rows * CELL_H + 38), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), f"{label_dir.name} | fixed random sample n={len(chosen)} | seed={SEED}", fill="black", font=font)
    for index, path in enumerate(chosen):
        image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        image.thumbnail((245, 185), Image.Resampling.LANCZOS)
        col, row = index % COLS, index // COLS
        x = col * CELL_W + (CELL_W - image.width) // 2
        y = 38 + row * CELL_H + 3
        canvas.paste(image, (x, y))
        draw.text((col * CELL_W + 5, 38 + row * CELL_H + 193), path.name, fill="black", font=font)
    canvas.save(OUT / f"review_{label_dir.name}.jpg", quality=91)
print(OUT.resolve())
