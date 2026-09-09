from pathlib import Path
import csv
from PIL import Image, ImageDraw, ImageFont, ImageOps

root = Path("research/dataset_11_curated")
csv_path = Path("research/audit_11class_quality/quality_metrics.csv")
out = Path("research/audit_11class_quality/flagged_contact_sheet.jpg")
with csv_path.open(encoding="utf-8", newline="") as handle:
    rows = [row for row in csv.DictReader(handle) if row["objective_flags"]]
cell_w, cell_h, cols = 320, 260, 3
rows_n = (len(rows) + cols - 1) // cols
canvas = Image.new("RGB", (cell_w * cols, cell_h * rows_n), "white")
draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()
for index, row in enumerate(rows):
    image = ImageOps.exif_transpose(Image.open(root / row["relative_path"])).convert("RGB")
    image.thumbnail((300, 205), Image.Resampling.LANCZOS)
    x = (index % cols) * cell_w + (cell_w - image.width) // 2
    y = (index // cols) * cell_h + 5
    canvas.paste(image, (x, y))
    tx, ty = (index % cols) * cell_w + 7, (index // cols) * cell_h + 214
    draw.text((tx, ty), Path(row["relative_path"]).name, fill="black", font=font)
    draw.text((tx, ty + 16), row["objective_flags"], fill="#9b1c1c", font=font)
out.parent.mkdir(parents=True, exist_ok=True)
canvas.save(out, quality=92)
print(out.resolve())
