from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--per-label", type=int, default=100)
    args = parser.parse_args()

    with args.candidate_manifest.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    counts = Counter(row["label"] for row in rows)
    if len(counts) != 11 or set(counts.values()) != {args.per_label}:
        raise RuntimeError(f"Expected 11 labels x {args.per_label}, got {dict(counts)}")
    existing_images = [
        path for path in args.destination.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ] if args.destination.exists() else []
    if existing_images:
        raise RuntimeError(f"Destination already contains {len(existing_images)} images")

    locked_rows: list[dict[str, str]] = []
    for row in rows:
        relative = Path(row["final_relative_path"])
        source = args.candidate / relative
        if not source.is_file() or sha256(source) != row["sha256"]:
            raise RuntimeError(f"Candidate missing or SHA mismatch: {relative}")
        target = args.destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha256(target) != row["sha256"]:
            raise RuntimeError(f"Locked copy SHA mismatch: {relative}")
        item = dict(row)
        item["locked_relative_path"] = relative.as_posix()
        locked_rows.append(item)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in locked_rows for key in row})
    with args.manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(locked_rows)

    content_lines = [f"{row['locked_relative_path']}\0{row['sha256']}\n" for row in locked_rows]
    content_sha = hashlib.sha256("".join(sorted(content_lines)).encode("utf-8")).hexdigest()
    lock = {
        "schema_version": "riceai-external-test-lock/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "locked",
        "dataset_root": str(args.destination.resolve()),
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256(args.manifest),
        "dataset_content_sha256": content_sha,
        "image_count": len(locked_rows),
        "class_count": len(counts),
        "counts": dict(sorted(counts.items())),
        "duplicate_policy": "unique SHA-256, decoded-pixel SHA-256, and canonical pHash within final set; pHash distance >8 versus dataset v3",
        "visual_review": "contact sheets reviewed; sticky-trap BPH and illustration excluded before lock",
        "evaluation_policy": "external test is evaluation-only and must not be used for model or hyperparameter selection",
    }
    args.lock.parent.mkdir(parents=True, exist_ok=True)
    args.lock.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(lock, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
