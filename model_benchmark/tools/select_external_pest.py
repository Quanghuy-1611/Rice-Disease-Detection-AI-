from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


MAPPING = {
    "Brown_Planthopper": "brown_planthopper",
    "LEAF_FOLDERS": "leaf_roller",
    "Stemz_Borer": "stem_borer",
}


def distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--v3-manifest", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    with args.inventory.open(encoding="utf-8-sig", newline="") as handle:
        inventory = list(csv.DictReader(handle))
    with args.v3_manifest.open(encoding="utf-8-sig", newline="") as handle:
        v3 = list(csv.DictReader(handle))
    v3_sha = {row["sha256"] for row in v3}
    v3_pixel = {row["pixel_sha256"] for row in v3}
    v3_phash = [row["phash"] for row in v3]

    eligible: list[dict[str, str]] = []
    mapped = 0
    rejection_counts: Counter[str] = Counter()
    for row in inventory:
        folder = row["relative_path"].split("/", 1)[0]
        if folder not in MAPPING:
            continue
        mapped += 1
        row["label"] = MAPPING[folder]
        nearest = min(distance(row["canonical_phash64"], value) for value in v3_phash)
        row["nearest_v3_phash_distance"] = str(nearest)
        reasons = []
        if row["sha256"] in v3_sha:
            reasons.append("sha256_vs_v3")
        if row["pixel_sha256"] in v3_pixel:
            reasons.append("pixel_sha256_vs_v3")
        if nearest <= 8:
            reasons.append("phash_le8_vs_v3")
        if min(int(row["width"]), int(row["height"])) < 224:
            reasons.append("min_dimension_lt224")
        if reasons:
            rejection_counts.update(reasons)
        else:
            eligible.append(row)

    selected: list[dict[str, str]] = []
    for label in MAPPING.values():
        pool = sorted(
            (row for row in eligible if row["label"] == label),
            key=lambda row: (-int(row["width"]) * int(row["height"]), row["relative_path"]),
        )
        kept: list[dict[str, str]] = []
        for row in pool:
            if all(distance(row["canonical_phash64"], other["canonical_phash64"]) > 8 for other in kept):
                kept.append(row)
            if len(kept) >= args.limit:
                break
        selected.extend(kept)

    conflict_indices: set[int] = set()
    for left_index, left in enumerate(selected):
        for right_index in range(left_index + 1, len(selected)):
            right = selected[right_index]
            if left["label"] != right["label"] and distance(left["canonical_phash64"], right["canonical_phash64"]) <= 8:
                conflict_indices.update((left_index, right_index))
    selected = [row for index, row in enumerate(selected) if index not in conflict_indices]

    counters: Counter[str] = Counter()
    for row in selected:
        counters[row["label"]] += 1
        suffix = Path(row["relative_path"]).suffix.lower()
        row["candidate_relative_path"] = f"{row['label']}/{row['label']}_{counters[row['label']]:03d}{suffix}"
        if not (args.candidate_root / row["candidate_relative_path"]).is_file():
            raise RuntimeError(f"Missing copied candidate: {row['candidate_relative_path']}")

    args.report_root.mkdir(parents=True, exist_ok=True)
    columns = list(selected[0]) if selected else []
    with (args.report_root / "external_selection_manifest_v1.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(selected)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Mendeley y5hwbhrn5m v1",
        "license": "CC BY 4.0",
        "status": "candidate_pending_visual_expert_review",
        "images_audited": len(inventory),
        "mapped_original_images": mapped,
        "eligible_vs_v3": len(eligible),
        "selected": dict(counters),
        "total_selected": len(selected),
        "cross_label_images_removed": len(conflict_indices),
        "rejection_counts": dict(rejection_counts),
        "policy": "original_data only; source-disjoint; SHA/pixel/pHash<=8 vs v3 excluded; min 224px; pHash>8 within and across selected labels",
    }
    (args.report_root / "external_selection_summary_v1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
