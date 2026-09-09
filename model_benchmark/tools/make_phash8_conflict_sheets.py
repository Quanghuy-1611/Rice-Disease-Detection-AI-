from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps

root = Path("research/dataset_11_curated")
data = json.loads(Path("research/audit_11class_selection/phash_threshold_sensitivity_v2.json").read_text(encoding="utf-8"))
pairs = [p for p in data["examples"] if p["distance"] <= 8 and p["left_label"] != p["right_label"]]
out = Path("research/audit_11class_selection/phash8_conflict_sheets")
out.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()
for page, start in enumerate(range(0, len(pairs), 9), 1):
    items = pairs[start:start + 9]
    canvas = Image.new("RGB", (720, 9 * 245), "white")
    draw = ImageDraw.Draw(canvas)
    for row, pair in enumerate(items):
        y = row * 245
        for side, key in enumerate(("left_path", "right_path")):
            image = ImageOps.exif_transpose(Image.open(root / pair[key])).convert("RGB")
            image.thumbnail((300, 190), Image.Resampling.LANCZOS)
            x = 20 + side * 360 + (300 - image.width) // 2
            canvas.paste(image, (x, y + 3))
            draw.text((5 + side * 360, y + 198), pair[key], fill="black", font=font)
        draw.text((300, y + 220), f"Hamming={pair['distance']}", fill="#9b1c1c", font=font)
    canvas.save(out / f"page_{page}.jpg", quality=80, optimize=True)
