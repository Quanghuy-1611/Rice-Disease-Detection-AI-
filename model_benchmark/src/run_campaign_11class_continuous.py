"""Run the locked 11-class benchmark continuously, one model at a time."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import ContractError, configure_utf8_console, load_locked_inputs, validate_campaign_lock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_11class_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_11class_v1.json"
MODEL_RUNNER = ROOT / "src" / "run_model_3seeds_11class.py"
TRAINING_ROOT = ROOT / "runs" / "training_11class_v1"
STATUS_PATH = ROOT / "runs" / "campaign_progress_11class_all_models.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_status(payload: dict[str, object]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at_utc"] = now()
    temporary = STATUS_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, STATUS_PATH)


def model_complete(model_id: str, seeds: list[int]) -> bool:
    for seed in seeds:
        run_dir = TRAINING_ROOT / model_id / f"seed_{seed}"
        manifest = run_dir / "run_manifest.json"
        checkpoint = run_dir / "best_model.pt"
        if not manifest.is_file() or not checkpoint.is_file():
            return False
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if payload.get("status") != "complete" or payload.get("test_evaluated") is not False:
            return False
    return True


def main() -> int:
    configure_utf8_console()
    parser = argparse.ArgumentParser(description="Run all locked models and seeds sequentially.")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    inputs = load_locked_inputs(CONTRACT)
    lock = validate_campaign_lock(inputs, CAMPAIGN_LOCK)
    models = list(inputs.contract["training"]["models_to_train"])
    seeds = [int(seed) for seed in inputs.contract["training"]["training_seeds"]]
    if args.validate_only:
        print(json.dumps({"status": "ready", "models": models, "seeds": seeds, "device": args.device}))
        return 0

    if lock.get("models_to_train") != models or lock.get("training_seeds") != seeds:
        raise ContractError("Campaign model/seed list differs from immutable lock")

    completed = [model for model in models if model_complete(model, seeds)]
    write_status({
        "status": "running",
        "started_at_utc": now(),
        "pid": os.getpid(),
        "models": models,
        "seeds": seeds,
        "completed_models": completed,
        "test_evaluated": False,
    })

    for position, model_id in enumerate(models, 1):
        if model_id in completed:
            print(f"SKIP COMPLETE MODEL [{position}/{len(models)}]: {model_id}", flush=True)
            continue
        write_status({
            "status": "running",
            "pid": os.getpid(),
            "current_model": model_id,
            "model_position": position,
            "model_count": len(models),
            "models": models,
            "seeds": seeds,
            "completed_models": completed,
            "test_evaluated": False,
        })
        print(f"START MODEL [{position}/{len(models)}]: {model_id}", flush=True)
        command = [
            sys.executable,
            str(MODEL_RUNNER),
            "--model", model_id,
            "--workers", str(args.workers),
            "--device", args.device,
        ]
        result = subprocess.run(command, cwd=ROOT.parent, check=False)
        if result.returncode != 0 or not model_complete(model_id, seeds):
            write_status({
                "status": "failed",
                "pid": os.getpid(),
                "failed_model": model_id,
                "exit_code": result.returncode,
                "models": models,
                "seeds": seeds,
                "completed_models": completed,
                "test_evaluated": False,
            })
            raise RuntimeError(f"Campaign stopped safely at {model_id}; inspect logs before resume")
        completed.append(model_id)
        print(f"COMPLETE MODEL [{position}/{len(models)}]: {model_id}", flush=True)

    write_status({
        "status": "complete",
        "pid": os.getpid(),
        "models": models,
        "seeds": seeds,
        "completed_models": completed,
        "test_evaluated": False,
    })
    print(f"CAMPAIGN COMPLETE: {len(models)} models x {len(seeds)} seeds; tests remain unevaluated.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, RuntimeError) as exc:
        print(f"CAMPAIGN STOPPED: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2)
