from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


HIGH_RISK = [
    "bacterial_leaf_blight", "blast", "brown_spot", "dead_heart",
    "normal", "tungro", "weeds",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-per-label", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    root = args.dataset.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with args.split.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_label_split = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["label"] in HIGH_RISK:
            by_label_split[row["label"]][row["split"]].append(row)
    queue = []
    targets = {"train": 70, "validation": 15, "test": 15}
    for label in HIGH_RISK:
        chosen = []
        for split, count in targets.items():
            pool = sorted(by_label_split[label][split], key=lambda row: row["relative_path"])
            rng = random.Random(f"{args.seed}:{label}:{split}")
            chosen.extend(rng.sample(pool, min(count, len(pool))))
        for number, row in enumerate(chosen, 1):
            queue.append({
                "review_id": f"{label}-{number:03d}",
                "current_label": label,
                "relative_path": row["relative_path"],
                "split": row["split"],
                "decision": "",
                "corrected_label": "",
                "reason": "",
                "reviewer": "",
            })
    fields = list(queue[0])
    with (args.output / "expert_review_queue.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(queue)

    font = ImageFont.load_default()
    for label in HIGH_RISK:
        items = [row for row in queue if row["current_label"] == label]
        for page, start in enumerate(range(0, len(items), 20), 1):
            page_items = items[start:start + 20]
            cols, cell_w, cell_h = 4, 260, 235
            rows_n = (len(page_items) + cols - 1) // cols
            canvas = Image.new("RGB", (cols * cell_w, 38 + rows_n * cell_h), "white")
            draw = ImageDraw.Draw(canvas)
            draw.text((8, 10), f"{label} | page {page} | seed={args.seed}", fill="black", font=font)
            for index, item in enumerate(page_items):
                image = ImageOps.exif_transpose(Image.open(root / item["relative_path"])).convert("RGB")
                image.thumbnail((245, 185), Image.Resampling.LANCZOS)
                col, row_n = index % cols, index // cols
                x = col * cell_w + (cell_w - image.width) // 2
                y = 38 + row_n * cell_h + 3
                canvas.paste(image, (x, y))
                draw.text((col * cell_w + 5, 38 + row_n * cell_h + 193), item["review_id"], fill="black", font=font)
                draw.text((col * cell_w + 5, 38 + row_n * cell_h + 208), Path(item["relative_path"]).name, fill="#444444", font=font)
            canvas.save(args.output / f"{label}_page_{page}.jpg", quality=88, optimize=True)


if __name__ == "__main__":
    main()
