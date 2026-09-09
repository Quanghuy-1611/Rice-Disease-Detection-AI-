from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps

root = Path("research/dataset_11_curated")
data = json.loads(Path("research/audit_11class_selection/cross_label_near_duplicates.json").read_text(encoding="utf-8"))
pairs = data["pairs"]
cell_w, row_h = 720, 260
canvas = Image.new("RGB", (cell_w, row_h * len(pairs)), "white")
draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()
for row, pair in enumerate(pairs):
    y = row * row_h
    for side, key in enumerate(("left_path", "right_path")):
        image = ImageOps.exif_transpose(Image.open(root / pair[key])).convert("RGB")
        image.thumbnail((300, 205), Image.Resampling.LANCZOS)
        x = 20 + side * 360 + (300 - image.width) // 2
        canvas.paste(image, (x, y + 5))
        draw.text((10 + side * 360, y + 215), pair[key], fill="black", font=font)
    draw.text((310, y + 238), f"Hamming={pair['distance']}", fill="#9b1c1c", font=font)
out = Path("research/audit_11class_selection/cross_label_pair_sheet.jpg")
canvas.save(out, quality=84, optimize=True)
