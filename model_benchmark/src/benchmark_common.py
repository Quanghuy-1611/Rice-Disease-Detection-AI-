"""Shared integrity utilities for the locked backbone benchmark.

This module deliberately has no TensorFlow/PyTorch imports: it can be run before
any expensive training job to prove that every architecture receives the same
data contract.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_MANIFEST_COLUMNS = {
    "relative_path",
    "label",
    "label_index",
    "sha256",
    "duplicate_count",
    "split",
}
VALID_SPLITS = {"train", "validation", "test"}


class ContractError(RuntimeError):
    """Raised if a benchmark input breaks the locked protocol."""


def configure_utf8_console() -> None:
    """Prevent Windows legacy code pages from crashing on Vietnamese paths."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")


@dataclass(frozen=True)
class LockedInputs:
    contract_path: Path
    contract: dict[str, Any]
    contract_sha256: str
    dataset_root: Path
    manifest_path: Path
    manifest_sha256: str
    metadata_path: Path
    metadata: dict[str, Any]
    canonical_classes: tuple[str, ...]
    split_counts: dict[str, int]
    class_split_counts: dict[str, dict[str, int]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Cannot read JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ContractError(f"JSON object expected: {path}")
    return payload


def resolve_contract_path(contract_path: Path, relative_path: str) -> Path:
    candidate = (contract_path.parent / relative_path).resolve()
    if not candidate.exists():
        raise ContractError(f"Required path does not exist: {candidate}")
    return candidate


def _require_equal(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ContractError(f"{name} mismatch: expected {expected!r}, got {actual!r}")


def _validate_contract_shape(contract: dict[str, Any]) -> None:
    _require_equal("contract schema_version", contract.get("schema_version"), "riceai-backbone-benchmark/v1")
    if not contract.get("benchmark_id"):
        raise ContractError("contract benchmark_id is required")
    models = contract.get("models")
    if not isinstance(models, list) or len(models) < 2 or len(models) != len(set(models)):
        raise ContractError("contract models must be a de-duplicated list with at least two entries")
    data = contract.get("data")
    if not isinstance(data, dict):
        raise ContractError("contract data object is required")
    for key in ("dataset_root", "split_manifest", "split_metadata", "manifest_id", "class_count"):
        if key not in data:
            raise ContractError(f"contract data.{key} is required")


def load_locked_inputs(contract_path: Path) -> LockedInputs:
    """Read and fully validate the contract, metadata and CSV split manifest."""
    contract_path = contract_path.resolve()
    contract = read_json(contract_path)
    _validate_contract_shape(contract)
    data = contract["data"]

    dataset_root = resolve_contract_path(contract_path, data["dataset_root"])
    manifest_path = resolve_contract_path(contract_path, data["split_manifest"])
    metadata_path = resolve_contract_path(contract_path, data["split_metadata"])
    metadata = read_json(metadata_path)
    manifest_sha = sha256_file(manifest_path)

    _require_equal("metadata schema_version", metadata.get("schema_version"), "riceai-image-split/v1")
    _require_equal("metadata manifest_id", metadata.get("manifest_id"), data["manifest_id"])
    _require_equal("metadata split_seed", metadata.get("split_seed"), data.get("split_seed"))
    _require_equal("metadata split_level", metadata.get("split_level"), data.get("split_level"))
    _require_equal(
        "metadata duplicate policy",
        metadata.get("cross_label_duplicate_policy"),
        data.get("cross_label_duplicate_policy"),
    )
    _require_equal("metadata fractions", metadata.get("fractions"), data.get("fractions"))
    _require_equal("metadata manifest_sha256", metadata.get("manifest_sha256"), manifest_sha)

    classes = metadata.get("canonical_classes")
    if not isinstance(classes, list) or len(classes) != data["class_count"] or len(classes) != len(set(classes)):
        raise ContractError("metadata canonical_classes is not a unique class map matching contract class_count")
    class_indices = metadata.get("class_indices")
    expected_indices = {str(index): label for index, label in enumerate(classes)}
    _require_equal("metadata class_indices", class_indices, expected_indices)

    split_counts: Counter[str] = Counter()
    class_split_counts: dict[str, Counter[str]] = {split: Counter() for split in VALID_SPLITS}
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(reader.fieldnames) != REQUIRED_MANIFEST_COLUMNS:
            raise ContractError(
                f"Manifest columns must be exactly {sorted(REQUIRED_MANIFEST_COLUMNS)}, got {reader.fieldnames}"
            )
        for line_number, row in enumerate(reader, start=2):
            split = row["split"]
            label = row["label"]
            if split not in VALID_SPLITS:
                raise ContractError(f"Invalid split at manifest line {line_number}: {split!r}")
            if label not in classes:
                raise ContractError(f"Unknown label at manifest line {line_number}: {label!r}")
            try:
                label_index = int(row["label_index"])
            except ValueError as exc:
                raise ContractError(f"Invalid label_index at manifest line {line_number}") from exc
            if label_index != classes.index(label):
                raise ContractError(f"Class index mismatch at manifest line {line_number}")
            if len(row["sha256"]) != 64:
                raise ContractError(f"Invalid SHA256 at manifest line {line_number}")
            if not row["relative_path"] or Path(row["relative_path"]).is_absolute():
                raise ContractError(f"Unsafe relative_path at manifest line {line_number}")
            split_counts[split] += 1
            class_split_counts[split][label] += 1

    if set(split_counts) != VALID_SPLITS:
        raise ContractError(f"Manifest is missing a split: found {dict(split_counts)}")
    expected_counts = metadata.get("split_class_counts")
    normalised_counts = {split: dict(class_split_counts[split]) for split in sorted(VALID_SPLITS)}
    _require_equal("manifest per-class split counts", normalised_counts, expected_counts)

    return LockedInputs(
        contract_path=contract_path,
        contract=contract,
        contract_sha256=sha256_file(contract_path),
        dataset_root=dataset_root,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha,
        metadata_path=metadata_path,
        metadata=metadata,
        canonical_classes=tuple(classes),
        split_counts=dict(split_counts),
        class_split_counts=normalised_counts,
    )


def build_provenance(inputs: LockedInputs) -> dict[str, Any]:
    """Return fields every run artifact must preserve verbatim."""
    return {
        "benchmark_id": inputs.contract["benchmark_id"],
        "contract_sha256": inputs.contract_sha256,
        "split_manifest": str(inputs.manifest_path),
        "split_manifest_sha256": inputs.manifest_sha256,
        "split_metadata": str(inputs.metadata_path),
        "dataset_root": str(inputs.dataset_root),
        "manifest_id": inputs.metadata["manifest_id"],
        "split_seed": inputs.metadata["split_seed"],
        "split_level": inputs.metadata["split_level"],
        "class_count": len(inputs.canonical_classes),
        "canonical_classes": list(inputs.canonical_classes),
        "split_counts": inputs.split_counts,
    }


def validate_campaign_lock(inputs: LockedInputs, lock_path: Path) -> dict[str, Any]:
    """Reject execution if protocol/code changed after campaign lock."""
    lock_path = lock_path.resolve()
    lock = read_json(lock_path)
    _require_equal("campaign lock schema", lock.get("schema_version"), "riceai-campaign-lock/v1")
    _require_equal("campaign contract SHA256", lock.get("contract_sha256"), inputs.contract_sha256)
    _require_equal("campaign split SHA256", lock.get("split_manifest_sha256"), inputs.manifest_sha256)
    code_hashes = lock.get("code_sha256")
    if not isinstance(code_hashes, dict) or not code_hashes:
        raise ContractError("campaign lock has no code_sha256 map")
    project_root = lock_path.parents[2]
    for relative_path, expected_sha in code_hashes.items():
        source_path = (project_root / relative_path).resolve()
        if not source_path.is_file():
            raise ContractError(f"Locked source file is missing: {source_path}")
        _require_equal(f"source SHA256 {relative_path}", sha256_file(source_path), expected_sha)
    return lock
