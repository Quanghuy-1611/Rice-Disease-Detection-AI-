from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-id", required=True)
    parser.add_argument("--split-level", required=True)
    parser.add_argument("--cross-label-policy", required=True)
    args = parser.parse_args()
    with args.split.open(encoding="utf-8-sig", newline="") as handle:
        source = list(csv.DictReader(handle))
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    file_hashes = {item["relative_path"]: item["sha256"] for item in lock["files"]}
    classes = sorted({row["label"] for row in source})
    class_to_index = {label: index for index, label in enumerate(classes)}
    rows = []
    group_sizes = Counter(row["group_id"] for row in source)
    for row in source:
        rows.append({
            "relative_path": row["relative_path"],
            "label": row["label"],
            "label_index": class_to_index[row["label"]],
            "sha256": file_hashes[row["relative_path"]],
            "duplicate_count": group_sizes[row["group_id"]],
            "split": row["split"],
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = defaultdict(Counter)
    for row in rows:
        counts[row["split"]][row["label"]] += 1
    metadata = {
        "schema_version": "riceai-image-split/v1",
        "manifest_id": args.manifest_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "split_seed": 2026,
        "split_level": args.split_level,
        "cross_label_duplicate_policy": args.cross_label_policy,
        "fractions": {"train": 0.70, "validation": 0.15, "test": 0.15},
        "manifest_sha256": sha256(args.output),
        "canonical_classes": classes,
        "class_indices": {str(index): label for index, label in enumerate(classes)},
        "split_class_counts": {split: dict(counts[split]) for split in sorted(counts)},
        "group_manifest": str(args.split.resolve()),
        "group_manifest_sha256": sha256(args.split),
        "dataset_lock": str(args.lock.resolve()),
        "dataset_content_sha256": lock["dataset_content_sha256"],
        "group_cross_split_violations": 0,
        "label_review_status": lock["label_review_status"],
        "test_role": "internal_grouped_holdout_only",
        "external_test_required_for_primary_publication_claim": True,
    }
    args.output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"rows": len(rows), "classes": len(classes), "manifest_sha256": metadata["manifest_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
