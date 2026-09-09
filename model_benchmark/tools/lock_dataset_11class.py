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
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.dataset.resolve()
    with args.manifest.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {row["relative_path"] for row in rows}
    if len(expected) != len(rows):
        raise RuntimeError("Duplicate relative_path in split manifest")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    missing, unlisted = sorted(expected - actual), sorted(actual - expected)
    group_splits = defaultdict(set)
    counts = Counter()
    file_entries = []
    aggregate = hashlib.sha256()
    for index, row in enumerate(sorted(rows, key=lambda item: item["relative_path"]), 1):
        path = root / row["relative_path"]
        digest = sha256(path)
        size = path.stat().st_size
        group_splits[row["group_id"]].add(row["split"])
        counts[(row["split"], row["label"])] += 1
        aggregate.update(f"{row['relative_path']}\0{size}\0{digest}\n".encode("utf-8"))
        file_entries.append({"relative_path": row["relative_path"], "bytes": size, "sha256": digest})
        if index % 1000 == 0 or index == len(rows):
            print(f"Hashed {index}/{len(rows)}", flush=True)
    violations = sorted(group for group, splits in group_splits.items() if len(splits) > 1)
    labels = sorted({row["label"] for row in rows})
    report = {
        "schema_version": "riceai-dataset-lock/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(root),
        "dataset_file_count": len(actual),
        "dataset_content_sha256": aggregate.hexdigest(),
        "split_manifest": str(args.manifest.resolve()),
        "split_manifest_sha256": sha256(args.manifest),
        "selection_manifest_sha256": sha256(args.selection),
        "labels": labels,
        "label_count": len(labels),
        "counts": {
            split: {label: counts[(split, label)] for label in labels}
            for split in ("train", "validation", "test")
        },
        "missing_manifest_files": missing,
        "unlisted_dataset_files": unlisted,
        "group_cross_split_violations": violations,
        "technical_integrity_passed": not missing and not unlisted and not violations and len(labels) == 11,
        "label_review_status": "pending_expert_confirmation_for_7_high-risk labels",
        "publication_status": "internal grouped split; not an external test set",
        "files": file_entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in (
        "dataset_file_count", "dataset_content_sha256", "split_manifest_sha256",
        "label_count", "technical_integrity_passed", "label_review_status",
        "publication_status",
    )}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
