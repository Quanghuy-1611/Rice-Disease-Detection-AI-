from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


LABELS = [
    "bacterial_leaf_blight", "blast", "brown_planthopper", "brown_spot",
    "dead_heart", "golden_apple_snail", "leaf_roller", "normal",
    "stem_borer", "tungro", "weeds",
]


def phash_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", nargs=3, metavar=("NAME", "ROOT", "MANIFEST"), required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.output_root.exists():
        raise SystemExit(f"Refusing existing output root: {args.output_root}")

    candidates: list[dict[str, str]] = []
    for source_name, root_text, manifest_text in args.input:
        root = Path(root_text).resolve()
        with Path(manifest_text).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            relative = row.get("final_relative_path") or row.get("final_candidate_relative_path") or row.get("candidate_relative_path")
            if not relative:
                continue
            row["merge_source"] = source_name
            row["merge_source_root"] = str(root)
            row["merge_source_relative_path"] = relative
            candidates.append(row)

    # Retain input priority while capping each class.
    counts: Counter[str] = Counter()
    capped: list[dict[str, str]] = []
    for row in candidates:
        label = row["label"]
        if counts[label] < args.limit:
            capped.append(row)
            counts[label] += 1

    # Exclude both sides of any exact/pixel/pHash<=8 collision across labels.
    conflicts: set[int] = set()
    conflict_pairs: Counter[str] = Counter()
    for left_index, left in enumerate(capped):
        for right_index in range(left_index + 1, len(capped)):
            right = capped[right_index]
            if left["label"] == right["label"]:
                continue
            collision = (
                left["sha256"] == right["sha256"]
                or left["pixel_sha256"] == right["pixel_sha256"]
                or phash_distance(left["canonical_phash64"], right["canonical_phash64"]) <= 8
            )
            if collision:
                conflicts.update((left_index, right_index))
                conflict_pairs[" | ".join(sorted((left["label"], right["label"])))] += 1
    selected = [row for index, row in enumerate(capped) if index not in conflicts]

    args.output_root.mkdir(parents=True)
    final_counts: Counter[str] = Counter()
    for row in selected:
        label = row["label"]
        final_counts[label] += 1
        source_path = Path(row["merge_source_root"]) / Path(row["merge_source_relative_path"])
        suffix = source_path.suffix.lower()
        relative = Path(label) / f"{label}_{final_counts[label]:03d}{suffix}"
        target = args.output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        if file_sha256(target) != row["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch after copy: {target}")
        row["final_relative_path"] = relative.as_posix()

    args.report_root.mkdir(parents=True, exist_ok=True)
    columns = sorted({key for row in selected for key in row})
    with (args.report_root / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(selected)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "candidate_pending_visual_expert_review",
        "cap_per_label": args.limit,
        "counts": {label: final_counts[label] for label in LABELS},
        "total": sum(final_counts.values()),
        "missing_to_100": {label: args.limit - final_counts[label] for label in LABELS if final_counts[label] < args.limit},
        "cross_label_conflict_images_removed": len(conflicts),
        "cross_label_conflict_pairs": dict(conflict_pairs),
        "inputs": [item[0] for item in args.input],
    }
    (args.report_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


