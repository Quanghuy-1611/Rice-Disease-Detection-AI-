from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--distance", type=int, default=4)
    args = parser.parse_args()
    with args.manifest.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values = [int(row["phash"], 16) for row in rows]
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, value in enumerate(values):
        for band in range(8):
            buckets[(band, (value >> (8 * band)) & 0xFF)].append(index)
    candidates = set()
    for indices in buckets.values():
        for pos, left in enumerate(indices):
            for right in indices[pos + 1:]:
                if rows[left]["label"] != rows[right]["label"]:
                    candidates.add((left, right) if left < right else (right, left))
    pairs = []
    for left, right in candidates:
        distance = (values[left] ^ values[right]).bit_count()
        if distance <= args.distance:
            pairs.append({
                "distance": distance,
                "left_label": rows[left]["label"],
                "left_path": rows[left]["curated_relative_path"],
                "right_label": rows[right]["label"],
                "right_path": rows[right]["curated_relative_path"],
            })
    pairs.sort(key=lambda row: (row["distance"], row["left_label"], row["left_path"]))
    result = {
        "method": "Cross-label canonical pHash64, LSH candidate generation, exact Hamming verification",
        "threshold": args.distance,
        "images": len(rows),
        "candidate_pairs": len(candidates),
        "cross_label_near_duplicate_pairs": len(pairs),
        "pairs": pairs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "pairs"}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
