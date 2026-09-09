from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def duplicate_groups(rows: list[dict[str, str]], key: str) -> list[list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        value = row.get(key, "").strip()
        if value:
            grouped[value].append(row)
    return [items for items in grouped.values() if len(items) > 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--expert-queue", type=Path, required=True)
    parser.add_argument(
        "--expert-policy",
        choices=("require_review", "retain_source_labels"),
        default="require_review",
    )
    parser.add_argument("--external-test", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    selection = read_csv(args.selection)
    split = read_csv(args.split)
    selection_by_path = {row["curated_relative_path"].replace("\\", "/"): row for row in selection}
    split_paths = {row["relative_path"].replace("\\", "/") for row in split}
    dataset_paths = {
        path.relative_to(args.dataset).as_posix()
        for path in args.dataset.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }

    groups_to_splits: dict[str, set[str]] = defaultdict(set)
    for row in split:
        groups_to_splits[row["group_id"]].add(row["split"])
    group_violations = sorted(group for group, values in groups_to_splits.items() if len(values) > 1)

    duplicate_audit = {}
    for key in ("sha256", "pixel_sha256"):
        groups = duplicate_groups(selection, key)
        duplicate_audit[key] = {
            "duplicate_groups": len(groups),
            "cross_label_groups": sum(len({row["label"] for row in items}) > 1 for items in groups),
            "cross_split_groups": sum(
                len({next(s["split"] for s in split if s["relative_path"].replace("\\", "/") == row["curated_relative_path"].replace("\\", "/")) for row in items}) > 1
                for items in groups
            ),
        }

    source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in selection:
        source_counts[row["label"]][row["source_root"]] += 1
    source_summary = {
        label: {"source_count": len(counts), "counts": dict(sorted(counts.items()))}
        for label, counts in sorted(source_counts.items())
    }

    review = read_csv(args.expert_queue)
    decisions = Counter((row.get("decision") or "").strip().lower() or "pending" for row in review)
    external_counts = Counter(
        path.parent.name
        for path in args.external_test.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )

    checks = {
        "dataset_matches_selection": dataset_paths == set(selection_by_path),
        "selection_matches_split": set(selection_by_path) == split_paths,
        "group_cross_split_violations_zero": not group_violations,
        "exact_file_cross_split_duplicates_zero": duplicate_audit["sha256"]["cross_split_groups"] == 0,
        "decoded_pixel_cross_split_duplicates_zero": duplicate_audit["pixel_sha256"]["cross_split_groups"] == 0,
        "expert_review_complete_or_waived": (
            decisions.get("pending", 0) == 0 or args.expert_policy == "retain_source_labels"
        ),
        "external_test_has_all_labels": set(source_counts) <= set(external_counts),
        "external_test_minimum_50_per_label": all(external_counts[label] >= 50 for label in source_counts),
    }
    technical_keys = [key for key in checks if not key.startswith("expert_") and not key.startswith("external_")]
    report = {
        "schema_version": "riceai-release-readiness-audit/v1",
        "inputs": {
            "dataset": str(args.dataset.resolve()),
            "selection": str(args.selection.resolve()),
            "split": str(args.split.resolve()),
            "split_sha256": sha256(args.split),
        },
        "counts": {
            "dataset_images": len(dataset_paths),
            "selection_rows": len(selection),
            "split_rows": len(split),
            "labels": len(source_counts),
            "split": dict(Counter(row["split"] for row in split)),
        },
        "duplicate_audit": duplicate_audit,
        "group_cross_split_violations": group_violations,
        "source_summary": source_summary,
        "labels_with_one_source": sorted(label for label, item in source_summary.items() if item["source_count"] == 1),
        "expert_review_decisions": dict(decisions),
        "expert_policy": args.expert_policy,
        "external_test_image_counts": dict(sorted(external_counts.items())),
        "checks": checks,
        "technical_integrity_passed": all(checks[key] for key in technical_keys),
        "official_training_allowed": all(checks.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks": checks, "technical_integrity_passed": report["technical_integrity_passed"], "official_training_allowed": report["official_training_allowed"]}, indent=2))


if __name__ == "__main__":
    main()
