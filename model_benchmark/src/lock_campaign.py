"""Create the immutable code/data lock before the first training run."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import (
    ContractError,
    configure_utf8_console,
    load_locked_inputs,
    read_json,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_v1.json"
PREFLIGHT = ROOT / "runs" / "preflight" / "preflight_latest.json"
MODEL_SMOKE = ROOT / "runs" / "preflight" / "model_smoke_latest.json"
TRAINING_SMOKE = ROOT / "runs" / "preflight" / "training_smoke_latest.json"
LOCK_PATH = ROOT / "config" / "campaign_lock_v1.json"
LOCKED_FILES = (
    "model_benchmark/config/benchmark_contract_v1.json",
    "model_benchmark/requirements.txt",
    "model_benchmark/src/benchmark_common.py",
    "model_benchmark/src/model_factory.py",
    "model_benchmark/src/prefetch_weights.py",
    "model_benchmark/src/smoke_models.py",
    "model_benchmark/src/smoke_training.py",
    "model_benchmark/src/preflight.py",
    "model_benchmark/src/train_backbone.py",
    "model_benchmark/src/run_campaign.py",
    "model_benchmark/src/final_evaluate.py",
    "model_benchmark/src/lock_campaign.py",
)


def main() -> int:
    configure_utf8_console()
    inputs = load_locked_inputs(CONTRACT)
    preflight = read_json(PREFLIGHT)
    if preflight.get("status") != "passed":
        raise ContractError("Latest preflight did not pass")
    preflight_provenance = preflight.get("provenance", {})
    if preflight_provenance.get("split_manifest_sha256") != inputs.manifest_sha256:
        raise ContractError("Preflight split manifest SHA is stale")
    if preflight_provenance.get("canonical_classes") != list(inputs.canonical_classes):
        raise ContractError("Preflight class map differs from the current data contract")
    if preflight_provenance.get("split_counts") != inputs.split_counts:
        raise ContractError("Preflight split counts differ from the current data contract")
    verification = preflight.get("image_verification", {})
    if verification.get("performed") is not True or verification.get("images_checked") != sum(inputs.split_counts.values()):
        raise ContractError("Full image SHA verification is required before campaign lock")
    smoke = read_json(MODEL_SMOKE)
    if smoke.get("status") != "passed":
        raise ContractError("Six-model CUDA smoke test did not pass")
    if smoke.get("split_manifest_sha256") != inputs.manifest_sha256:
        raise ContractError("Model smoke report uses a different split")
    smoke_models = [item.get("model_id") for item in smoke.get("models", [])]
    if smoke_models != inputs.contract["models"] or any(
        item.get("status") != "passed" for item in smoke.get("models", [])
    ):
        raise ContractError("Model smoke report does not contain all locked models in order")
    training_smoke = read_json(TRAINING_SMOKE)
    if training_smoke.get("status") != "passed":
        raise ContractError("Six-model training-path smoke test did not pass")
    training_smoke_models = [item.get("model_id") for item in training_smoke.get("models", [])]
    if training_smoke_models != inputs.contract["models"] or any(
        item.get("status") != "passed" for item in training_smoke.get("models", [])
    ):
        raise ContractError("Training smoke report does not contain all locked models in order")
    training_root = ROOT / "runs" / "training"
    if training_root.exists() and any(training_root.rglob("best_model.pt")):
        raise ContractError("Training checkpoints already exist; refusing to create a new campaign lock")
    if LOCK_PATH.exists():
        raise ContractError(f"Campaign lock already exists; refusing overwrite: {LOCK_PATH}")

    project_root = ROOT.parent
    code_hashes: dict[str, str] = {}
    for relative in LOCKED_FILES:
        path = project_root / relative
        if not path.is_file():
            raise ContractError(f"Cannot lock missing file: {path}")
        code_hashes[relative] = sha256_file(path)
    payload = {
        "schema_version": "riceai-campaign-lock/v1",
        "campaign_id": inputs.contract["benchmark_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": inputs.contract_sha256,
        "split_manifest_sha256": inputs.manifest_sha256,
        "preflight_report_sha256": sha256_file(PREFLIGHT),
        "model_smoke_report_sha256": sha256_file(MODEL_SMOKE),
        "training_smoke_report_sha256": sha256_file(TRAINING_SMOKE),
        "full_image_verification": verification,
        "models": inputs.contract["models"],
        "models_to_train": inputs.contract["training"]["models_to_train"],
        "training_seeds": inputs.contract["training"]["training_seeds"],
        "code_sha256": code_hashes,
    }
    LOCK_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("CAMPAIGN LOCKED")
    print(f"Lock: {LOCK_PATH}")
    print(f"Lock SHA256: {sha256_file(LOCK_PATH)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"CAMPAIGN LOCK FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
