"""Run or resume the locked 6-model x 3-seed training campaign sequentially."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import (
    ContractError,
    configure_utf8_console,
    load_locked_inputs,
    read_json,
    validate_campaign_lock,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_v1.json"
TRAIN_SCRIPT = ROOT / "src" / "train_backbone.py"
TRAINING_ROOT = ROOT / "runs" / "training"
PROGRESS_PATH = ROOT / "runs" / "campaign_progress.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run/resume the locked RiceAI training campaign.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    parser.add_argument("--only-model", default=None, help="Optional one-model pilot; must be locked.")
    parser.add_argument("--only-seed", type=int, default=None, help="Optional one-seed pilot; must be locked.")
    return parser.parse_args()


def write_progress(payload: dict[str, object]) -> None:
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_complete(run_dir: Path) -> bool:
    manifest_path = run_dir / "run_manifest.json"
    checkpoint_path = run_dir / "best_model.pt"
    if not manifest_path.is_file() or not checkpoint_path.is_file():
        return False
    manifest = read_json(manifest_path)
    return manifest.get("status") == "complete" and manifest.get("test_evaluated") is False


def main() -> int:
    configure_utf8_console()
    args = parse_args()
    inputs = load_locked_inputs(CONTRACT)
    validate_campaign_lock(inputs, CAMPAIGN_LOCK)
    models = list(inputs.contract["training"]["models_to_train"])
    seeds = list(inputs.contract["training"]["training_seeds"])
    if args.only_model is not None:
        if args.only_model not in models:
            raise ContractError(f"--only-model is not locked: {args.only_model}")
        models = [args.only_model]
    if args.only_seed is not None:
        if args.only_seed not in seeds:
            raise ContractError(f"--only-seed is not locked: {args.only_seed}")
        seeds = [args.only_seed]

    selected_runs = [(model_id, seed) for model_id in models for seed in seeds]
    completed: list[str] = []
    for index, (model_id, seed) in enumerate(selected_runs, start=1):
        run_key = f"{model_id}/seed_{seed}"
        run_dir = TRAINING_ROOT / model_id / f"seed_{seed}"
        if is_complete(run_dir):
            print(f"SKIP COMPLETE [{index}/{len(selected_runs)}]: {run_key}", flush=True)
            completed.append(run_key)
            continue
        if run_dir.exists() and any(run_dir.iterdir()):
            raise ContractError(
                f"Partial/non-complete run requires manual diagnosis; refusing overwrite: {run_dir}"
            )
        write_progress(
            {
                "status": "running",
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                "current_run": run_key,
                "position": index,
                "selected_run_count": len(selected_runs),
                "completed": completed,
            }
        )
        print(f"START [{index}/{len(selected_runs)}]: {run_key}", flush=True)
        command = [
            sys.executable,
            str(TRAIN_SCRIPT),
            "--model",
            model_id,
            "--seed",
            str(seed),
            "--workers",
            str(args.workers),
            "--device",
            args.device,
        ]
        completed_process = subprocess.run(command, cwd=ROOT.parent, check=False)
        if completed_process.returncode != 0:
            write_progress(
                {
                    "status": "failed",
                    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "failed_run": run_key,
                    "exit_code": completed_process.returncode,
                    "completed": completed,
                }
            )
            raise RuntimeError(f"Training failed: {run_key}, exit code {completed_process.returncode}")
        if not is_complete(run_dir):
            raise RuntimeError(f"Training exited successfully but artifacts are incomplete: {run_key}")
        completed.append(run_key)

    write_progress(
        {
            "status": "complete",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "selected_run_count": len(selected_runs),
            "completed": completed,
            "test_evaluated": False,
        }
    )
    print(f"CAMPAIGN SELECTION COMPLETE: {len(completed)} run(s); test remains locked.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"CAMPAIGN REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
