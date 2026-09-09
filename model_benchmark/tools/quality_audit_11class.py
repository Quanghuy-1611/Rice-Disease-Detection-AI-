from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def metrics(path: Path) -> dict[str, float | int | str]:
    with Image.open(path) as src:
        image = ImageOps.exif_transpose(src).convert("RGB")
        width, height = image.size
        thumb = image.copy()
        thumb.thumbnail((256, 256), Image.Resampling.LANCZOS)
        gray = np.asarray(thumb.convert("L"), dtype=np.float32)
    gx = np.diff(gray, axis=1)
    gy = np.diff(gray, axis=0)
    sharpness = float((np.var(gx) + np.var(gy)) / 2.0)
    hist = np.bincount(gray.astype(np.uint8).ravel(), minlength=256).astype(np.float64)
    probs = hist[hist > 0] / hist.sum()
    entropy = float(-np.sum(probs * np.log2(probs)))
    dark = float(np.mean(gray <= 10))
    bright = float(np.mean(gray >= 245))
    return {
        "width": width,
        "height": height,
        "min_dimension": min(width, height),
        "aspect_ratio": width / height,
        "sharpness": sharpness,
        "entropy": entropy,
        "dark_fraction": dark,
        "bright_fraction": bright,
        "mean_brightness": float(np.mean(gray)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.dataset.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)
    rows = []
    failures = []
    for i, path in enumerate(files, 1):
        rel = path.relative_to(root).as_posix()
        try:
            row = {"relative_path": rel, "label": rel.split("/", 1)[0], **metrics(path)}
            reasons = []
            if row["min_dimension"] < 128:
                reasons.append("dimension_below_128")
            if not 0.4 <= row["aspect_ratio"] <= 2.5:
                reasons.append("extreme_aspect_ratio")
            if row["entropy"] < 3.0:
                reasons.append("very_low_entropy")
            if row["dark_fraction"] > 0.80:
                reasons.append("mostly_black")
            if row["bright_fraction"] > 0.80:
                reasons.append("mostly_white")
            row["objective_flags"] = ";".join(reasons)
            rows.append(row)
        except Exception as exc:
            failures.append({"relative_path": rel, "error": f"{type(exc).__name__}: {exc}"})
        if i % 1000 == 0 or i == len(files):
            print(f"Processed {i}/{len(files)}", flush=True)

    by_label = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)
    summary = {}
    for label, items in sorted(by_label.items()):
        sharp = np.array([x["sharpness"] for x in items])
        summary[label] = {
            "count": len(items),
            "sharpness_p01": float(np.percentile(sharp, 1)),
            "sharpness_p05": float(np.percentile(sharp, 5)),
            "sharpness_median": float(np.median(sharp)),
            "objective_flag_count": sum(bool(x["objective_flags"]) for x in items),
        }
    fields = list(rows[0]) if rows else []
    with (args.output / "quality_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (args.output / "quality_summary.json").write_text(json.dumps({
        "dataset": str(root), "count": len(rows), "decode_failures": failures,
        "automatic_exclusion_policy": "Only objective flags; blur is reported for review, not auto-excluded.",
        "per_class": summary,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
