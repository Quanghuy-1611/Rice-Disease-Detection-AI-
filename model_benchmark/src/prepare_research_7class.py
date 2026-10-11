"""Prepare a genuine seven-output research campaign without touching legacy runs."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import load_locked_inputs, sha256_file


PROJECT = Path(__file__).resolve().parents[2]
BENCHMARK = PROJECT / "model_benchmark"
SPLITS = PROJECT / "research" / "splits"
SOURCE = SPLITS / "dataset_11_research_v3_train_validation.csv"
SOURCE_METADATA = SPLITS / "dataset_11_research_v3_train_validation.metadata.json"
OLD_CONTRACT = BENCHMARK / "config" / "benchmark_contract_research_v3_stablefp32.json"
MANIFEST = SPLITS / "research_7class_train_validation.csv"
METADATA = SPLITS / "research_7class_train_validation.metadata.json"
CONTRACT = BENCHMARK / "config" / "benchmark_contract_research_7class.json"
LOCK = BENCHMARK / "config" / "campaign_lock_research_7class.json"
CLASSES = [
    "bacterial_leaf_blight", "brown_spot", "golden_apple_snail",
    "leaf_roller", "normal", "tungro", "weeds",
]
MODELS = ["mobilenetv2", "mobilenetv3large", "resnet18", "efficientnetb0", "shufflenetv2_1_0x"]
CODE = [
    "model_benchmark/src/benchmark_common.py",
    "model_benchmark/src/model_factory.py",
    "model_benchmark/src/train_backbone.py",
    "model_benchmark/src/run_campaign_research_7class.py",
]


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    targets = [MANIFEST, METADATA, CONTRACT, LOCK]
    if any(path.exists() for path in targets):
        raise SystemExit("Seven-class protocol already exists; refusing to overwrite any locked artifact.")
    original = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    if sha256_file(SOURCE) != original["manifest_sha256"]:
        raise SystemExit("Original split changed; refusing to derive seven-class split.")
    root = PROJECT / "research" / "dataset_11_collection_pool_v3"
    counts = {"train": Counter(), "validation": Counter()}
    selected = []
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        if not fields or not {"label", "label_index", "split", "relative_path", "sha256"} <= set(fields):
            raise SystemExit("Original split has an unexpected schema.")
        for row in reader:
            if row["label"] not in CLASSES:
                continue
            path = (root / row["relative_path"]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise SystemExit(f"Missing or unsafe source image: {row['relative_path']}")
            if row["split"] not in counts:
                raise SystemExit(f"Unexpected split: {row['split']}")
            row["label_index"] = str(CLASSES.index(row["label"]))
            counts[row["split"]][row["label"]] += 1
            selected.append(row)
    if len(selected) != 29329 or any(counts[split][label] == 0 for split in counts for label in CLASSES):
        raise SystemExit(f"Unexpected seven-class counts: {counts}")
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)
    metadata = {
        "schema_version": "riceai-image-split/v1",
        "manifest_id": "research_7class_train_validation",
        "status": "LOCKED_FOR_SEVEN_CLASS_TRAINING",
        "split_seed": original["split_seed"],
        "split_level": original["split_level"],
        "split_method": original["split_method"],
        "fractions": original["fractions"],
        "cross_label_duplicate_policy": original["cross_label_duplicate_policy"],
        "canonical_classes": CLASSES,
        "class_indices": {str(index): label for index, label in enumerate(CLASSES)},
        "dataset_root": str(root),
        "parent_manifest": str(SOURCE),
        "parent_manifest_sha256": sha256_file(SOURCE),
        "manifest_sha256": sha256_file(MANIFEST),
        "total_images": len(selected),
        "split_class_counts": {split: dict(counts[split]) for split in sorted(counts)},
        "method_note": "Retains original train/validation assignment; no external-test images added.",
    }
    write_json(METADATA, metadata)
    contract = json.loads(OLD_CONTRACT.read_text(encoding="utf-8-sig"))
    contract["benchmark_id"] = "rice_7class_research_v1"
    contract["task"]["description"] = "Phan loai bay nhan lua tu anh RGB."
    contract["data"].update({
        "split_manifest": "../../research/splits/research_7class_train_validation.csv",
        "split_metadata": "../../research/splits/research_7class_train_validation.metadata.json",
        "manifest_id": metadata["manifest_id"], "class_count": 7,
        "external_test_root": None, "external_test_manifest": None,
        "external_test_lock_file": None,
        "external_test_role": "new_blind_seven_class_set_required_before_final_claim",
    })
    contract["models"] = MODELS
    contract["training"]["models_to_train"] = MODELS
    contract["release_gates"] = {
        "training_allowed": True,
        "final_external_evaluation_allowed": False,
        "reason": "Fresh seven-class external test has not been collected and locked.",
    }
    contract["integrity_rules"] = [
        "All runs train a seven-output classifier on the same train/validation split.",
        "Select checkpoints and compare models using validation only.",
        "Previously viewed external-test images are not a new blind test.",
        "No external-test inference is performed by this campaign.",
    ]
    write_json(CONTRACT, contract)
    inputs = load_locked_inputs(CONTRACT)
    lock = {
        "schema_version": "riceai-campaign-lock/v1",
        "campaign_id": "rice_7class_research_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": inputs.contract_sha256,
        "split_manifest_sha256": inputs.manifest_sha256,
        "split_metadata_sha256": sha256_file(METADATA),
        "parent_manifest_sha256": sha256_file(SOURCE),
        "models_to_train": MODELS,
        "training_seeds": contract["training"]["training_seeds"],
        "code_sha256": {relative: sha256_file(PROJECT / relative) for relative in CODE},
        "external_test_evaluated_by_training_pipeline": False,
    }
    write_json(LOCK, lock)
    print(json.dumps({"status": "ready", "classes": CLASSES,
                      "train": sum(counts["train"].values()),
                      "validation": sum(counts["validation"].values()),
                      "models": MODELS, "seeds": lock["training_seeds"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
