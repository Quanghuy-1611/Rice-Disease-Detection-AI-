from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--block", type=int, default=256)
    args = parser.parse_args()
    with args.selection.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with args.split.open(encoding="utf-8-sig", newline="") as handle:
        split_map = {row["relative_path"]: row["split"] for row in csv.DictReader(handle)}
    hashes = np.array([int(row["phash"], 16) for row in rows], dtype=np.uint64)
    labels = np.array([row["label"] for row in rows], dtype=object)
    splits = np.array([split_map[row["curated_relative_path"]] for row in rows], dtype=object)
    thresholds = (2, 4, 6, 8, 10)
    counts = {str(t): {"all": 0, "cross_label": 0, "cross_split": 0,
                       "cross_label_and_cross_split": 0} for t in thresholds}
    examples = []
    for start in range(0, len(rows), args.block):
        stop = min(start + args.block, len(rows))
        distances = np.bitwise_count(np.bitwise_xor(hashes[start:stop, None], hashes[None, :]))
        left_local, right = np.where(distances <= max(thresholds))
        left = left_local + start
        keep = right > left
        left, right = left[keep], right[keep]
        d = distances[left_local[keep], right]
        cross_label = labels[left] != labels[right]
        cross_split = splits[left] != splits[right]
        for threshold in thresholds:
            mask = d <= threshold
            counts[str(threshold)]["all"] += int(mask.sum())
            counts[str(threshold)]["cross_label"] += int((mask & cross_label).sum())
            counts[str(threshold)]["cross_split"] += int((mask & cross_split).sum())
            counts[str(threshold)]["cross_label_and_cross_split"] += int((mask & cross_label & cross_split).sum())
        interesting = (d <= 8) & (cross_label | cross_split)
        for i, j, distance in zip(left[interesting], right[interesting], d[interesting]):
            if len(examples) < 20000:
                examples.append({
                    "distance": int(distance),
                    "left_path": rows[int(i)]["curated_relative_path"],
                    "left_label": rows[int(i)]["label"],
                    "left_split": splits[int(i)],
                    "right_path": rows[int(j)]["curated_relative_path"],
                    "right_label": rows[int(j)]["label"],
                    "right_split": splits[int(j)],
                })
        print(f"Compared left rows {start}-{stop - 1}", flush=True)
    examples.sort(key=lambda row: (row["distance"], row["left_label"], row["left_path"]))
    result = {
        "method": "Exhaustive all-pairs canonical pHash64 Hamming distance using NumPy blocks",
        "images": len(rows), "threshold_counts": counts,
        "stored_examples_threshold": 8,
        "stored_examples": len(examples), "examples": examples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"images": len(rows), "threshold_counts": counts,
                      "stored_examples": len(examples)}, indent=2))


if __name__ == "__main__":
    main()
