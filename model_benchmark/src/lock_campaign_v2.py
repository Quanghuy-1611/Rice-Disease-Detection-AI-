"""Lock campaign v2 without mutating the auditable v1 campaign."""

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
CONTRACT = ROOT / "config" / "benchmark_contract_v2.json"
PREFLIGHT = ROOT / "runs" / "preflight" / "preflight_latest.json"
MODEL_SMOKE = ROOT / "runs" / "preflight" / "model_smoke_latest.json"
TRAINING_SMOKE = ROOT / "runs" / "preflight" / "training_smoke_latest.json"
LOCK_PATH = ROOT / "config" / "campaign_lock_v2.json"
V1_LOCK = ROOT / "config" / "campaign_lock_v1.json"
V1_PILOT_MANIFEST = ROOT / "runs" / "training" / "mobilenetv2" / "seed_42" / "run_manifest.json"
LOCKED_FILES = (
    "model_benchmark/config/benchmark_contract_v2.json",
    "model_benchmark/requirements.txt",
    "model_benchmark/src/benchmark_common.py",
    "model_benchmark/src/model_factory.py",
    "model_benchmark/src/train_backbone.py",
    "model_benchmark/src/run_campaign.py",
    "model_benchmark/src/final_evaluate.py",
    "model_benchmark/src/train_backbone_v2.py",
    "model_benchmark/src/run_campaign_v2.py",
    "model_benchmark/src/final_evaluate_v2.py",
    "model_benchmark/src/lock_campaign_v2.py",
)


def main() -> int:
    configure_utf8_console()
    inputs = load_locked_inputs(CONTRACT)
    preflight = read_json(PREFLIGHT)
    provenance = preflight.get("provenance", {})
    if preflight.get("status") != "passed":
        raise ContractError("Latest preflight did not pass")
    if provenance.get("split_manifest_sha256") != inputs.manifest_sha256:
        raise ContractError("Preflight split manifest SHA is stale")
    if provenance.get("canonical_classes") != list(inputs.canonical_classes):
        raise ContractError("Preflight class map differs")
    if provenance.get("split_counts") != inputs.split_counts:
        raise ContractError("Preflight split counts differ")
    verification = preflight.get("image_verification", {})
    if verification.get("performed") is not True or verification.get("images_checked") != sum(inputs.split_counts.values()):
        raise ContractError("Full image SHA verification is required")

    for report_path, label in ((MODEL_SMOKE, "model"), (TRAINING_SMOKE, "training")):
        report = read_json(report_path)
        report_models = [item.get("model_id") for item in report.get("models", [])]
        if report.get("status") != "passed" or report_models != inputs.contract["models"]:
            raise ContractError(f"Six-model {label} smoke report is invalid")
        if any(item.get("status") != "passed" for item in report.get("models", [])):
            raise ContractError(f"At least one {label} smoke check failed")

    training_root = ROOT / "runs" / "training_v2"
    if training_root.exists() and any(training_root.rglob("best_model.pt")):
        raise ContractError("V2 training checkpoints already exist; refusing a new lock")
    if LOCK_PATH.exists():
        raise ContractError(f"V2 campaign lock already exists: {LOCK_PATH}")
    if not V1_LOCK.is_file() or not V1_PILOT_MANIFEST.is_file():
        raise ContractError("V1 lock/pilot audit evidence is missing")

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
        "superseded_v1_lock_sha256": sha256_file(V1_LOCK),
        "excluded_v1_pilot_manifest_sha256": sha256_file(V1_PILOT_MANIFEST),
        "full_image_verification": verification,
        "models": inputs.contract["models"],
        "models_to_train": inputs.contract["training"]["models_to_train"],
        "training_seeds": inputs.contract["training"]["training_seeds"],
        "code_sha256": code_hashes,
    }
    LOCK_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("CAMPAIGN V2 LOCKED")
    print(f"Lock: {LOCK_PATH}")
    print(f"Lock SHA256: {sha256_file(LOCK_PATH)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"CAMPAIGN V2 LOCK FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
