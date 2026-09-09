from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


LABELS = (
    "bacterial_leaf_blight",
    "blast",
    "brown_planthopper",
    "brown_spot",
    "dead_heart",
    "golden_apple_snail",
    "leaf_roller",
    "normal",
    "stem_borer",
    "tungro",
    "weeds",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def rank(row: dict[str, str]) -> tuple[int, int, int, str]:
    """Prefer a larger, higher-resolution representative deterministically."""
    return (
        int(row.get("area") or 0),
        int(row.get("min_dimension") or 0),
        int(row.get("bytes") or 0),
        row["source_path"],
    )


def same_or_below(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the large 11-class dataset without touching the locked external test set."
    )
    parser.add_argument("--dataset-v4", type=Path, required=True)
    parser.add_argument("--all-candidates", type=Path, required=True)
    parser.add_argument("--curated-selection", type=Path, required=True)
    parser.add_argument("--external-manifest", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--output-dataset", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    parser.add_argument("--external-phash-distance", type=int, default=8)
    args = parser.parse_args()

    dataset_v4 = args.dataset_v4.resolve()
    external_root = args.external_root.resolve()
    output_dataset = args.output_dataset.resolve()
    staging = output_dataset.with_name(output_dataset.name + ".staging")
    output_audit = args.output_audit.resolve()
    if output_dataset.exists() or staging.exists():
        raise RuntimeError(f"Refusing to overwrite an existing dataset/staging directory: {output_dataset}")

    all_candidates = read_csv(args.all_candidates)
    curated = read_csv(args.curated_selection)
    external = read_csv(args.external_manifest)
    v4_rows = [row for row in all_candidates if Path(row["source_root"]).resolve() == dataset_v4]
    curated_outside = [
        row for row in curated if Path(row["source_root"]).resolve() != dataset_v4
    ]
    candidates = v4_rows + curated_outside

    if {row["label"] for row in candidates} != set(LABELS):
        raise RuntimeError("Candidate labels do not match the canonical 11 labels")
    for row in candidates:
        source = Path(row["source_path"]).resolve()
        if same_or_below(source, external_root):
            raise RuntimeError(f"External-test path entered candidate pool: {source}")
        if not source.is_file():
            raise FileNotFoundError(source)

    exclusion_counts: Counter[str] = Counter()
    excluded_examples: dict[str, list[str]] = defaultdict(list)

    def exclude(reason: str, rows: list[dict[str, str]]) -> None:
        exclusion_counts[reason] += len(rows)
        room = 25 - len(excluded_examples[reason])
        if room > 0:
            excluded_examples[reason].extend(row["source_path"] for row in rows[:room])

    # A decoded-pixel collision across labels is unsafe, so quarantine all sides.
    by_pixel: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        by_pixel[row["pixel_sha256"]].append(row)
    pixel_safe: list[dict[str, str]] = []
    for rows in by_pixel.values():
        if len({row["label"] for row in rows}) > 1:
            exclude("cross_label_exact_pixel_conflict", rows)
            continue
        ordered = sorted(rows, key=rank, reverse=True)
        pixel_safe.append(ordered[0])
        exclude("same_label_exact_pixel_redundant", ordered[1:])

    # Exact canonical-pHash equality is the conservative duplicate screen used by
    # the existing project curation. Keep the best representative per label.
    by_phash: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pixel_safe:
        by_phash[row["phash"]].append(row)
    phash_safe: list[dict[str, str]] = []
    for rows in by_phash.values():
        if len({row["label"] for row in rows}) > 1:
            exclude("cross_label_exact_phash_conflict", rows)
            continue
        ordered = sorted(rows, key=rank, reverse=True)
        phash_safe.append(ordered[0])
        exclude("same_label_exact_phash_redundant", ordered[1:])

    ext_by_label: dict[str, list[dict[str, str]]] = defaultdict(list)
    ext_sha = {row["sha256"] for row in external}
    ext_pixel = {row["pixel_sha256"] for row in external}
    for row in external:
        ext_by_label[row["label"]].append(row)

    selected: list[dict[str, str]] = []
    nearest_external_distances: list[int] = []
    for row in phash_safe:
        if row["sha256"] in ext_sha or row["pixel_sha256"] in ext_pixel:
            exclude("external_test_exact_overlap", [row])
            continue
        value = int(row["phash"], 16)
        distances = [
            (value ^ int(ext["canonical_phash64"], 16)).bit_count()
            for ext in ext_by_label[row["label"]]
        ]
        nearest = min(distances)
        nearest_external_distances.append(nearest)
        if nearest <= args.external_phash_distance:
            exclude("external_test_phash_le_threshold", [row])
            continue
        selected.append(row)

    selected.sort(key=lambda row: (row["label"], row["source_path"]))
    staging.mkdir(parents=True)
    output_rows: list[dict[str, str]] = []
    counters: Counter[str] = Counter()
    try:
        for number, row in enumerate(selected, 1):
            label = row["label"]
            counters[label] += 1
            suffix = Path(row["source_path"]).suffix.lower()
            if suffix not in {".jpg", ".jpeg", ".png"}:
                suffix = ".jpg"
            relative = f"{label}/{label}_{counters[label]:06d}{suffix}"
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(row["source_path"], target)
            item = dict(row)
            item["curated_relative_path"] = relative
            output_rows.append(item)
            if number % 1000 == 0 or number == len(selected):
                print(f"Copied {number}/{len(selected)}", flush=True)
        staging.rename(output_dataset)
    except Exception:
        # Keep staging for diagnosis; never delete source data automatically.
        raise

    output_audit.mkdir(parents=True, exist_ok=True)
    selection_path = output_audit / "selected_large_manifest_v1.csv"
    columns = list(output_rows[0])
    with selection_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(output_rows)

    report = {
        "schema_version": "riceai-large-11class-build/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "dataset_v4": str(dataset_v4),
            "dataset_v4_candidates": len(v4_rows),
            "curated_outside_v4_candidates": len(curated_outside),
            "raw_union_candidates": len(candidates),
            "external_test_root": str(external_root),
            "external_test_images": len(external),
        },
        "policy": {
            "same_label_exact_pixel": "keep highest-resolution deterministic representative",
            "same_label_exact_canonical_phash": "keep highest-resolution deterministic representative",
            "cross_label_exact_pixel_or_phash": "exclude all conflicting sides",
            "external_test": (
                "exclude byte/pixel exact matches and same-label canonical-pHash "
                f"Hamming distance <= {args.external_phash_distance}"
            ),
            "class_cap": None,
        },
        "selected_images": len(output_rows),
        "selected_class_counts": dict(sorted(counters.items())),
        "exclusion_counts": dict(sorted(exclusion_counts.items())),
        "excluded_examples": dict(excluded_examples),
        "nearest_external_phash_distance_after_exact_phash_filter": {
            "minimum_seen_before_external_exclusion": min(nearest_external_distances),
            "required_selected_minimum": args.external_phash_distance + 1,
        },
        "external_test_used_for_training": False,
        "selection_manifest": str(selection_path),
        "output_dataset": str(output_dataset),
    }
    (output_audit / "build_summary_v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "selected_images": len(output_rows),
        "selected_class_counts": report["selected_class_counts"],
        "exclusion_counts": report["exclusion_counts"],
        "output_dataset": str(output_dataset),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
