"""Run all six large-data models and three seeds sequentially and resumably."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import ContractError, configure_utf8_console, load_locked_inputs, read_json, validate_campaign_lock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_11class_large_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_11class_large_v1.json"
MODEL_RUNNER = ROOT / "src" / "run_model_3seeds_11class_large.py"
TRAINING_ROOT = ROOT / "runs" / "training_11class_large_v1"
STATUS_PATH = ROOT / "runs" / "campaign_progress_11class_large_v1.json"


def complete(model: str, seeds: list[int]) -> bool:
    for seed in seeds:
        run_dir = TRAINING_ROOT / model / f"seed_{seed}"
        manifest = run_dir / "run_manifest.json"
        if not manifest.is_file() or not (run_dir / "best_model.pt").is_file():
            return False
        if read_json(manifest).get("status") != "complete":
            return False
    return True


def status(payload: dict[str, object]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    temporary = STATUS_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, STATUS_PATH)


def main() -> int:
    configure_utf8_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    inputs = load_locked_inputs(CONTRACT)
    lock = validate_campaign_lock(inputs, CAMPAIGN_LOCK)
    models = list(inputs.contract["training"]["models_to_train"])
    seeds = [int(seed) for seed in inputs.contract["training"]["training_seeds"]]
    if lock.get("models_to_train") != models or lock.get("training_seeds") != seeds:
        raise ContractError("Model/seed list differs from immutable lock")
    if args.validate_only:
        print(json.dumps({"status": "ready", "models": models, "seeds": seeds}))
        return 0

    completed: list[str] = []
    for position, model in enumerate(models, 1):
        if complete(model, seeds):
            completed.append(model)
            print(f"SKIP COMPLETE MODEL [{position}/{len(models)}]: {model}", flush=True)
            continue
        status({"status": "running", "current_model": model, "model_position": position,
                "model_count": len(models), "completed_models": completed,
                "seeds": seeds, "pid": os.getpid(), "external_test_evaluated": False})
        result = subprocess.run([
            sys.executable, str(MODEL_RUNNER), "--model", model,
            "--workers", str(args.workers), "--device", args.device,
        ], cwd=ROOT.parent, check=False)
        if result.returncode != 0 or not complete(model, seeds):
            status({"status": "failed", "failed_model": model, "completed_models": completed,
                    "seeds": seeds, "pid": os.getpid(), "external_test_evaluated": False})
            raise RuntimeError(f"Campaign stopped safely at {model}")
        completed.append(model)
    status({"status": "complete", "completed_models": completed, "seeds": seeds,
            "pid": os.getpid(), "external_test_evaluated": False})
    print("LARGE CAMPAIGN COMPLETE; external test remains unevaluated.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, RuntimeError) as exc:
        print(f"LARGE CAMPAIGN STOPPED: {exc}", file=sys.stderr)
        raise SystemExit(2)
