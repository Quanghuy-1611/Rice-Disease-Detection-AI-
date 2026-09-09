"""Create the immutable lock for the large 11-class campaign."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import ContractError, load_locked_inputs, read_json, sha256_file


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
CONTRACT = ROOT / "config" / "benchmark_contract_11class_large_v1.json"
LOCK = ROOT / "config" / "campaign_lock_11class_large_v1.json"
DATASET_LOCK = PROJECT / "research" / "locks" / "dataset_11_large_v1.lock.json"
BUILD_REPORT = PROJECT / "research" / "audit_11class_large_v1" / "build_summary_v1.json"
EXTERNAL_LOCK = PROJECT / "research" / "external_test_11class_lock_v1.json"
EXTERNAL_MANIFEST = PROJECT / "research" / "external_test_11class_manifest_v1.csv"
CODE = (
    "model_benchmark/src/benchmark_common.py",
    "model_benchmark/src/model_factory.py",
    "model_benchmark/src/train_backbone.py",
    "model_benchmark/src/run_model_3seeds_11class_large.py",
    "model_benchmark/src/run_campaign_11class_large_continuous.py",
)


def main() -> int:
    if LOCK.exists():
        raise ContractError(f"Refusing to overwrite campaign lock: {LOCK}")
    inputs = load_locked_inputs(CONTRACT)
    dataset_lock = read_json(DATASET_LOCK)
    build = read_json(BUILD_REPORT)
    external = read_json(EXTERNAL_LOCK)
    if not dataset_lock.get("technical_integrity_passed"):
        raise ContractError("Large dataset lock did not pass integrity checks")
    if build.get("external_test_used_for_training") is not False:
        raise ContractError("Build report does not prove external-test isolation")
    if external.get("status") != "locked" or external.get("image_count") != 1100:
        raise ContractError("External-test lock is invalid")
    if external.get("manifest_sha256") != sha256_file(EXTERNAL_MANIFEST):
        raise ContractError("External-test manifest changed")
    training_root = ROOT / "runs" / "training_11class_large_v1"
    if training_root.exists() and any(training_root.rglob("best_model.pt")):
        raise ContractError("Large-data checkpoints already exist")
    payload = {
        "schema_version": "riceai-campaign-lock/v1",
        "campaign_id": inputs.contract["benchmark_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": inputs.contract_sha256,
        "split_manifest_sha256": inputs.manifest_sha256,
        "dataset_lock_sha256": sha256_file(DATASET_LOCK),
        "build_report_sha256": sha256_file(BUILD_REPORT),
        "external_test_manifest_sha256": sha256_file(EXTERNAL_MANIFEST),
        "external_test_lock_sha256": sha256_file(EXTERNAL_LOCK),
        "models": inputs.contract["models"],
        "models_to_train": inputs.contract["training"]["models_to_train"],
        "training_seeds": inputs.contract["training"]["training_seeds"],
        "code_sha256": {relative: sha256_file(PROJECT / relative) for relative in CODE},
    }
    LOCK.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LARGE CAMPAIGN LOCKED: {LOCK}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"LOCK FAILED: {exc}")
        raise SystemExit(2)
