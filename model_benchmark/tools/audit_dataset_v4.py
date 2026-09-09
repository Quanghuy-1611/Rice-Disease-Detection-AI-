from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pixel_digest(image: Image.Image) -> str:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    digest = hashlib.sha256()
    digest.update(f"{rgb.width}x{rgb.height}:RGB:".encode("ascii"))
    digest.update(rgb.tobytes())
    return digest.hexdigest()


def dct_matrix(size: int = 32, keep: int = 8) -> np.ndarray:
    x = np.arange(size, dtype=np.float64)
    k = np.arange(keep, dtype=np.float64)[:, None]
    matrix = np.cos((np.pi / size) * (x + 0.5) * k)
    matrix[0] *= np.sqrt(1.0 / size)
    matrix[1:] *= np.sqrt(2.0 / size)
    return matrix


DCT = dct_matrix()


def phash64(image: Image.Image) -> int:
    gray = ImageOps.exif_transpose(image).convert("L").resize((32, 32), Image.Resampling.LANCZOS)
    values = np.asarray(gray, dtype=np.float64)
    coeff = DCT @ values @ DCT.T
    low = coeff[:8, :8].reshape(-1)
    median = float(np.median(low[1:]))
    bits = low > median
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def canonical_phash(image: Image.Image) -> int:
    base = ImageOps.exif_transpose(image).convert("RGB")
    variants = []
    current = base
    for _ in range(4):
        variants.append(current)
        variants.append(ImageOps.mirror(current))
        current = current.rotate(90, expand=True)
    return min(phash64(item) for item in variants)


def duplicate_groups(records: list[dict[str, object]], key: str) -> list[list[int]]:
    buckets: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        buckets[str(record[key])].append(index)
    return [indices for indices in buckets.values() if len(indices) > 1]


def summarize_groups(records: list[dict[str, object]], groups: list[list[int]]) -> dict[str, object]:
    cross_label = []
    same_label = []
    for group in groups:
        payload = [str(records[index]["relative_path"]) for index in group]
        labels = sorted({str(records[index]["label"]) for index in group})
        item = {"labels": labels, "files": payload}
        (cross_label if len(labels) > 1 else same_label).append(item)
    return {
        "group_count": len(groups),
        "files_in_groups": sum(len(group) for group in groups),
        "redundant_files": sum(len(group) - 1 for group in groups),
        "same_label_group_count": len(same_label),
        "cross_label_group_count": len(cross_label),
        "same_label_groups": same_label,
        "cross_label_groups": cross_label,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit dataset_v4 without modifying source images.")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataset = args.dataset.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path for path in dataset.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    records: list[dict[str, object]] = []
    corrupt: list[dict[str, str]] = []
    for number, path in enumerate(files, 1):
        relative = path.relative_to(dataset).as_posix()
        label = relative.split("/", 1)[0]
        try:
            byte_sha = sha256_file(path)
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                mode = image.mode
                normalized_sha = pixel_digest(image)
                perceptual = canonical_phash(image)
            records.append({
                "relative_path": relative,
                "label": label,
                "bytes": path.stat().st_size,
                "width": width,
                "height": height,
                "mode": mode,
                "sha256": byte_sha,
                "pixel_sha256": normalized_sha,
                "canonical_phash64": f"{perceptual:016x}",
            })
        except Exception as exc:
            corrupt.append({"relative_path": relative, "error": f"{type(exc).__name__}: {exc}"})
        if number % 1000 == 0 or number == len(files):
            print(f"Processed {number}/{len(files)}", flush=True)

    exact = summarize_groups(records, duplicate_groups(records, "sha256"))
    pixel = summarize_groups(records, duplicate_groups(records, "pixel_sha256"))
    phash = summarize_groups(records, duplicate_groups(records, "canonical_phash64"))
    class_counts = Counter(str(record["label"]) for record in records)
    report = {
        "schema_version": "riceai-dataset-audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(dataset),
        "method": {
            "byte_duplicate": "SHA-256 over original file bytes",
            "pixel_duplicate": "SHA-256 over EXIF-normalized RGB dimensions and decoded pixels",
            "perceptual_duplicate": "Exact equality of a canonical 64-bit pHash across rotations and mirror transforms; candidate screen, not proof of duplicate",
        },
        "image_files_found": len(files),
        "valid_images": len(records),
        "corrupt_images": corrupt,
        "class_counts": dict(sorted(class_counts.items())),
        "exact_byte_duplicates": exact,
        "exact_decoded_pixel_duplicates": pixel,
        "exact_canonical_phash_matches": phash,
    }
    with (output / "dataset_v4_audit.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    with (output / "dataset_v4_inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        columns = ["relative_path", "label", "bytes", "width", "height", "mode", "sha256", "pixel_sha256", "canonical_phash64"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps({
        "image_files_found": len(files),
        "valid_images": len(records),
        "corrupt_images": len(corrupt),
        "exact_byte_redundant": exact["redundant_files"],
        "pixel_redundant": pixel["redundant_files"],
        "phash_exact_redundant": phash["redundant_files"],
        "output": str(output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
