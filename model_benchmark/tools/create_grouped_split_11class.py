from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DSU:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[b] = a


def cluster(rows: list[dict[str, str]], threshold: int) -> list[list[int]]:
    hashes = [int(row["phash"], 16) for row in rows]
    dsu = DSU(len(rows))
    # Exhaustive comparison is deliberate. The previous 8-bit LSH shortcut was
    # complete only for thresholds <= 7; at distance 8, one changed bit in each
    # byte can leave no equal band and silently miss a near-duplicate pair.
    # Each class currently has <= 900 images, so exact O(n^2) comparison is small
    # enough and gives an auditable no-false-negative grouping rule.
    for left, left_hash in enumerate(hashes):
        for right in range(left + 1, len(hashes)):
            if (left_hash ^ hashes[right]).bit_count() <= threshold:
                dsu.union(left, right)
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(rows)):
        groups[dsu.find(index)].append(index)
    return list(groups.values())


def allocate(groups: list[list[int]], count: int, rng: random.Random) -> dict[int, str]:
    rng.shuffle(groups)
    groups.sort(key=len, reverse=True)
    targets = {"train": round(count * 0.70), "validation": round(count * 0.15)}
    targets["test"] = count - targets["train"] - targets["validation"]
    assigned = {name: 0 for name in targets}
    result = {}
    for group_index, group in enumerate(groups):
        split = max(targets, key=lambda name: (targets[name] - assigned[name], -assigned[name]))
        for item_index in group:
            result[item_index] = split
        assigned[split] += len(group)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--phash-distance", type=int, default=4)
    args = parser.parse_args()
    root = args.dataset.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.selection.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_label: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        relative = row["source_relative"]
        # The physical curated name is recorded by the selection manifest.
        relative = row.get("relative_path") or row.get("curated_relative") or relative
        by_label[row["label"]].append(row)
    output_rows = []
    group_stats = {}
    rng = random.Random(args.seed)
    for label, items in sorted(by_label.items()):
        groups = cluster(items, args.phash_distance)
        assignments = allocate(groups, len(items), rng)
        group_for_index = {}
        for number, group in enumerate(groups, 1):
            group_id = f"{label}_g{number:04d}"
            for index in group:
                group_for_index[index] = group_id
        for index, row in enumerate(items):
            rel = row["relative_path"] if "relative_path" in row else row["source_relative"]
            # Selection CSV written by the curation step uses curated path when present.
            rel = row.get("curated_relative_path") or rel
            path = root / rel
            if not path.is_file():
                raise FileNotFoundError(path)
            output_rows.append({
                "relative_path": rel.replace("\\", "/"),
                "label": label,
                "split": assignments[index],
                "group_id": group_for_index[index],
                "phash64": row["phash"],
                "source_path": row["source_path"],
            })
        group_stats[label] = {
            "images": len(items), "groups": len(groups),
            "largest_group": max(map(len, groups)),
        }
    output_rows.sort(key=lambda row: (row["split"], row["label"], row["relative_path"]))
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    counts = defaultdict(lambda: defaultdict(int))
    groups_by_split = {}
    for row in output_rows:
        counts[row["label"]][row["split"]] += 1
        previous = groups_by_split.setdefault(row["group_id"], row["split"])
        if previous != row["split"]:
            raise RuntimeError(f"Group leakage: {row['group_id']}")
    metadata = {
        "schema_version": "riceai-grouped-split-11class/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_root": str(root), "seed": args.seed,
        "ratios": {"train": 0.70, "validation": 0.15, "test": 0.15},
        "grouping": f"canonical pHash64 connected components at Hamming distance <= {args.phash_distance}",
        "manifest_sha256": file_sha256(args.output),
        "selection_manifest_sha256": file_sha256(args.selection),
        "counts": {label: dict(value) for label, value in sorted(counts.items())},
        "group_stats": group_stats,
        "group_cross_split_violations": 0,
    }
    args.output.with_suffix(".metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metadata["counts"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
