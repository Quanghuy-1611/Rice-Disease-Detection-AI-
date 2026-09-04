"""Validate the immutable data/protocol contract before a benchmark run.

Example:
    python model_benchmark/src/preflight.py
    python model_benchmark/src/preflight.py --verify-images
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import (
    ContractError,
    build_provenance,
    configure_utf8_console,
    load_locked_inputs,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "config" / "benchmark_contract_v1.json"


def verify_images(
    manifest_path: Path,
    dataset_root: Path,
    total_images: int,
    progress_every: int = 1000,
) -> dict[str, int]:
    """Expensive optional check: prove each path and source image SHA matches CSV."""
    checked = 0
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            image_path = (dataset_root / row["relative_path"]).resolve()
            try:
                image_path.relative_to(dataset_root.resolve())
            except ValueError as exc:
                raise ContractError(f"Image path escaped dataset root: {row['relative_path']}") from exc
            if not image_path.is_file():
                raise ContractError(f"Missing source image: {image_path}")
            actual_sha = sha256_file(image_path)
            if actual_sha != row["sha256"]:
                raise ContractError(f"Image SHA mismatch: {row['relative_path']}")
            checked += 1
            if checked % progress_every == 0 or checked == total_images:
                percent = 100.0 * checked / total_images
                print(
                    f"Image verification: {checked:,}/{total_images:,} ({percent:.1f}%)",
                    flush=True,
                )
    return {"images_checked": checked}


def main() -> int:
    configure_utf8_console()
    parser = argparse.ArgumentParser(description="Validate RiceAI backbone benchmark contract.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--verify-images",
        action="store_true",
        help="Hash every locked source image; slow but required before first training campaign.",
    )
    args = parser.parse_args()

    try:
        inputs = load_locked_inputs(args.contract)
        verification = (
            verify_images(
                inputs.manifest_path,
                inputs.dataset_root,
                total_images=sum(inputs.split_counts.values()),
            )
            if args.verify_images
            else {}
        )
    except ContractError as exc:
        print(f"PREFLIGHT FAILED: {exc}", file=sys.stderr)
        return 2

    report = {
        "schema_version": "riceai-benchmark-preflight/v1",
        "status": "passed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": build_provenance(inputs),
        "per_class_split_counts": inputs.class_split_counts,
        "image_verification": {
            "performed": args.verify_images,
            **verification,
        },
    }
    report_dir = ROOT / "runs" / "preflight"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "preflight_latest.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PREFLIGHT PASSED")
    print(f"Report: {report_path}")
    print(f"Locked manifest SHA256: {inputs.manifest_sha256}")
    print(f"Images by split: {inputs.split_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
