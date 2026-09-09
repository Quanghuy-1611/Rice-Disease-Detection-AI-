from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--v3-manifest", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-license", required=True)
    parser.add_argument("--source-version", default="")
    parser.add_argument("--relative-prefix", default="")
    parser.add_argument("--internal-phash-threshold", type=int, default=8)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    inventory = read_csv(args.inventory)
    v3 = read_csv(args.v3_manifest)
    v3_sha = {row["sha256"] for row in v3}
    v3_pixel = {row["pixel_sha256"] for row in v3}
    v3_phash = [row["phash"] for row in v3]
    eligible: list[dict[str, str]] = []
    rejection_counts: Counter[str] = Counter()

    for row in inventory:
        if args.relative_prefix and not Path(row["relative_path"]).as_posix().startswith(args.relative_prefix):
            continue
        row["label"] = args.label
        row["source_name"] = args.source_name
        row["source_url"] = args.source_url
        row["source_license"] = args.source_license
        row["source_version"] = args.source_version
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
            eligible.append(row)

    eligible.sort(key=lambda row: (-int(row["width"]) * int(row["height"]), row["relative_path"]))
    selected: list[dict[str, str]] = []
    for candidate in eligible:
        if all(hamming(candidate["canonical_phash64"], kept["canonical_phash64"]) > args.internal_phash_threshold for kept in selected):
            selected.append(candidate)
            if len(selected) >= args.limit:
                break

    if args.output_root.exists():
        raise SystemExit(f"Refusing existing output root: {args.output_root}")
    args.output_root.mkdir(parents=True)
    args.report_root.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(selected, 1):
        suffix = Path(row["relative_path"]).suffix.lower()
        relative = Path(args.label) / f"{args.label}_{index:03d}{suffix}"
        target = args.output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.source_root / row["relative_path"], target)
        row["candidate_relative_path"] = relative.as_posix()

    columns = list(selected[0]) if selected else []
    with (args.report_root / "external_selection_manifest_v1.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(selected)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": args.source_name,
        "source_url": args.source_url,
        "source_license": args.source_license,
        "source_version": args.source_version,
        "label": args.label,
        "status": "candidate_pending_visual_expert_review",
        "images_audited": len(inventory),
        "eligible_vs_v3": len(eligible),
        "selected": len(selected),
        "rejection_counts": dict(rejection_counts),
        "policy": f"SHA/pixel/pHash<=8 vs v3 excluded; min 224px; pHash>{args.internal_phash_threshold} within selection",
    }
    (args.report_root / "external_selection_summary_v1.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
