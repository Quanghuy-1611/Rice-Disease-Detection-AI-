from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--labels", nargs="*")
    args = parser.parse_args()
    labels = args.labels or sorted(path.name for path in args.dataset.iterdir() if path.is_dir())
    args.output.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

    for label in labels:
        files = sorted(path for path in (args.dataset / label).iterdir() if path.suffix.lower() in extensions)
        cols, cell_w, cell_h = 10, 180, 155
        rows = (len(files) + cols - 1) // cols
        canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
        draw = ImageDraw.Draw(canvas)
        for index, path in enumerate(files):
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((170, 125), Image.Resampling.LANCZOS)
            cell_x = (index % cols) * cell_w
            cell_y = (index // cols) * cell_h
            x = cell_x + (cell_w - image.width) // 2
            y = cell_y + 3
            canvas.paste(image, (x, y))
            draw.text((cell_x + 4, cell_y + 132), path.stem[-3:], fill="black", font=font)
        target = args.output / f"{label}.jpg"
        canvas.save(target, quality=90)
        print(target.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
