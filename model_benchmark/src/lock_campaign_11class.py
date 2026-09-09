"""Create the immutable 11-class campaign lock after all release gates pass."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import ContractError, configure_utf8_console, load_locked_inputs, read_json, sha256_file


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
CONTRACT = ROOT / "config" / "benchmark_contract_11class_v1.json"
LOCK_PATH = ROOT / "config" / "campaign_lock_11class_v1.json"
PREFLIGHT = ROOT / "runs" / "preflight" / "preflight_latest.json"
MODEL_SMOKE = ROOT / "runs" / "preflight" / "model_smoke_latest.json"
TRAINING_SMOKE = ROOT / "runs" / "preflight" / "training_smoke_latest.json"
EXTERNAL_LOCK = PROJECT_ROOT / "research" / "external_test_11class_lock_v1.json"
EXTERNAL_MANIFEST = PROJECT_ROOT / "research" / "external_test_11class_manifest_v1.csv"
LOCKED_FILES = (
    "model_benchmark/config/benchmark_contract_11class_v1.json",
    "model_benchmark/requirements.txt",
    "model_benchmark/src/benchmark_common.py",
    "model_benchmark/src/model_factory.py",
    "model_benchmark/src/train_backbone.py",
    "model_benchmark/src/run_model_3seeds_11class.py",
)


def main() -> int:
    configure_utf8_console()
    inputs = load_locked_inputs(CONTRACT)
    gates = inputs.contract.get("release_gates", {})
    if gates.get("training_allowed") is not True or not str(gates.get("external_test_lock", "")).startswith("locked_"):
        raise ContractError("Release gates do not permit official training")

    preflight = read_json(PREFLIGHT)
    provenance = preflight.get("provenance", {})
    if preflight.get("status") != "passed" or preflight.get("image_verification", {}).get("performed") is not True:
        raise ContractError("Full preflight is not current and passed")
    if provenance.get("contract_sha256") != inputs.contract_sha256:
        raise ContractError("Preflight contract SHA is stale")
    if provenance.get("split_manifest_sha256") != inputs.manifest_sha256:
        raise ContractError("Preflight split SHA is stale")

    for report_path, label in ((MODEL_SMOKE, "model"), (TRAINING_SMOKE, "training")):
        report = read_json(report_path)
        models = [item.get("model_id") for item in report.get("models", [])]
        if report.get("status") != "passed" or report.get("contract_sha256") != inputs.contract_sha256:
            raise ContractError(f"{label} smoke report is stale or failed")
        if models != inputs.contract["models"] or any(item.get("status") != "passed" for item in report["models"]):
            raise ContractError(f"{label} smoke report does not cover all locked models")

    external = read_json(EXTERNAL_LOCK)
    if external.get("status") != "locked" or external.get("image_count") != 1100 or external.get("class_count") != 11:
        raise ContractError("External test lock is invalid")
    if external.get("manifest_sha256") != sha256_file(EXTERNAL_MANIFEST):
        raise ContractError("External test manifest SHA is stale")
    training_root = ROOT / "runs" / "training_11class_v1"
    if training_root.exists() and any(training_root.rglob("best_model.pt")):
        raise ContractError("11-class checkpoints already exist; refusing a new campaign lock")
    if LOCK_PATH.exists():
        raise ContractError(f"Campaign lock already exists: {LOCK_PATH}")

    code_hashes = {}
    for relative in LOCKED_FILES:
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise ContractError(f"Cannot lock missing file: {path}")
        code_hashes[relative] = sha256_file(path)
    payload = {
        "schema_version": "riceai-campaign-lock/v1",
        "campaign_id": inputs.contract["benchmark_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": inputs.contract_sha256,
        "split_manifest_sha256": inputs.manifest_sha256,
        "external_test_manifest_sha256": sha256_file(EXTERNAL_MANIFEST),
        "external_test_lock_sha256": sha256_file(EXTERNAL_LOCK),
        "preflight_report_sha256": sha256_file(PREFLIGHT),
        "model_smoke_report_sha256": sha256_file(MODEL_SMOKE),
        "training_smoke_report_sha256": sha256_file(TRAINING_SMOKE),
        "full_image_verification": preflight["image_verification"],
        "models": inputs.contract["models"],
        "models_to_train": inputs.contract["training"]["models_to_train"],
        "training_seeds": inputs.contract["training"]["training_seeds"],
        "code_sha256": code_hashes,
    }
    LOCK_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("11-CLASS CAMPAIGN LOCKED")
    print(f"Lock: {LOCK_PATH}")
    print(f"Lock SHA256: {sha256_file(LOCK_PATH)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"11-CLASS CAMPAIGN LOCK FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
