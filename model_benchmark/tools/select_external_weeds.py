from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--v3-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
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

    valid: list[dict[str, str]] = []
    rejection_counts: Counter[str] = Counter()
    for row in inventory:
        parts = Path(row["relative_path"]).parts
        species = parts[1] if len(parts) > 2 else parts[0]
        row["label"] = "weeds"
        row["source_subclass"] = species
        row["nearest_v3_phash_distance"] = str(
            min(hamming(row["canonical_phash64"], value) for value in v3_phash)
        )
        reasons = []
        if row["sha256"] in v3_sha:
            reasons.append("sha256_vs_v3")
        if row["pixel_sha256"] in v3_pixel:
            reasons.append("pixel_sha256_vs_v3")
        if int(row["nearest_v3_phash_distance"]) <= 8:
            reasons.append("phash_le8_vs_v3")
        if min(int(row["width"]), int(row["height"])) < 224:
            reasons.append("min_dimension_lt224")
        row["exclusion_reason"] = ";".join(reasons)
        if reasons:
            rejection_counts.update(reasons)
        else:
            valid.append(row)

    by_species: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in valid:
        by_species[row["source_subclass"]].append(row)
    for rows in by_species.values():
        rows.sort(key=lambda row: (-int(row["width"]) * int(row["height"]), row["relative_path"]))

    selected: list[dict[str, str]] = []
    positions = {species: 0 for species in by_species}
    species_order = sorted(by_species)
    while len(selected) < args.limit:
        added = False
        for species in species_order:
            rows = by_species[species]
            while positions[species] < len(rows):
                candidate = rows[positions[species]]
                positions[species] += 1
                if all(hamming(candidate["canonical_phash64"], kept["canonical_phash64"]) > 8 for kept in selected):
                    selected.append(candidate)
                    added = True
                    break
            if len(selected) >= args.limit:
                break
        if not added:
            break

    args.output_root.mkdir(parents=True, exist_ok=False)
    args.report_root.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(selected, 1):
        suffix = Path(row["relative_path"]).suffix.lower()
        relative = Path("weeds") / f"weeds_{index:03d}{suffix}"
        target = args.output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.source_root / Path(row["relative_path"]), target)
        row["candidate_relative_path"] = relative.as_posix()

    columns = list(selected[0]) if selected else []
    with (args.report_root / "external_selection_manifest_v1.csv").open("w" if False else "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(selected)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Mendeley mt72bmxz73 v3",
        "license": "CC BY 4.0",
        "status": "candidate_pending_visual_expert_review",
        "images_audited": len(inventory),
        "eligible_vs_v3": len(valid),
        "selected": len(selected),
        "selected_by_species": dict(Counter(row["source_subclass"] for row in selected)),
        "rejection_counts": dict(rejection_counts),
        "policy": "source-disjoint; SHA/pixel/pHash<=8 vs v3 excluded; min 224px; pHash>8 within selection; round-robin across weed species",
    }
    (args.report_root / "external_selection_summary_v1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
