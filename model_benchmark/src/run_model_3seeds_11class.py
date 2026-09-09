"""Run or resume one locked 11-class model across all configured seeds."""

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
CONTRACT = ROOT / "config" / "benchmark_contract_11class_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_11class_v1.json"
TRAIN_SCRIPT = ROOT / "src" / "train_backbone.py"
TRAINING_ROOT = ROOT / "runs" / "training_11class_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one 11-class model sequentially for every locked seed."
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    return parser.parse_args()


def is_complete(run_dir: Path) -> bool:
    manifest_path = run_dir / "run_manifest.json"
    checkpoint_path = run_dir / "best_model.pt"
    if not manifest_path.is_file() or not checkpoint_path.is_file():
        return False
    manifest = read_json(manifest_path)
    return manifest.get("status") == "complete" and manifest.get("test_evaluated") is False


def write_progress(model_id: str, payload: dict[str, object]) -> None:
    path = ROOT / "runs" / f"campaign_progress_11class_{model_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_console()
    args = parse_args()
    inputs = load_locked_inputs(CONTRACT)
    contract = inputs.contract
    gates = contract.get("release_gates", {})
    if gates.get("training_allowed") is not True:
        pending = [name for name, value in gates.items() if value == "pending"]
        raise ContractError(
            "11-class training is still blocked; pending gates: "
            + (", ".join(pending) or "unspecified")
        )
    validate_campaign_lock(inputs, CAMPAIGN_LOCK)

    models = list(contract["training"]["models_to_train"])
    seeds = list(contract["training"]["training_seeds"])
    if args.model not in models:
        raise ContractError(f"--model is not locked in the contract: {args.model}")

    completed: list[int] = []
    for position, seed in enumerate(seeds, 1):
        run_dir = TRAINING_ROOT / args.model / f"seed_{seed}"
        if is_complete(run_dir):
            print(f"SKIP COMPLETE [{position}/{len(seeds)}]: {args.model}/seed_{seed}", flush=True)
            completed.append(seed)
            continue
        if run_dir.exists() and any(run_dir.iterdir()):
            raise ContractError(f"Partial run requires diagnosis; refusing overwrite: {run_dir}")

        write_progress(args.model, {
            "status": "running",
            "model": args.model,
            "current_seed": seed,
            "position": position,
            "seed_count": len(seeds),
            "completed_seeds": completed,
            "test_evaluated": False,
        })
        print(f"START [{position}/{len(seeds)}]: {args.model}/seed_{seed}", flush=True)
        command = [
            sys.executable,
            str(TRAIN_SCRIPT),
            "--model", args.model,
            "--seed", str(seed),
            "--workers", str(args.workers),
            "--device", args.device,
            "--contract", str(CONTRACT),
            "--campaign-lock", str(CAMPAIGN_LOCK),
            "--output-root", str(TRAINING_ROOT),
        ]
        result = subprocess.run(command, cwd=ROOT.parent, check=False)
        if result.returncode != 0:
            write_progress(args.model, {
                "status": "failed",
                "model": args.model,
                "failed_seed": seed,
                "exit_code": result.returncode,
                "completed_seeds": completed,
                "test_evaluated": False,
            })
            raise RuntimeError(f"Training failed: {args.model}/seed_{seed}")
        if not is_complete(run_dir):
            raise RuntimeError(f"Training exited without complete artifacts: {run_dir}")
        completed.append(seed)

    write_progress(args.model, {
        "status": "complete",
        "model": args.model,
        "seed_count": len(seeds),
        "completed_seeds": completed,
        "test_evaluated": False,
    })
    print(f"MODEL COMPLETE: {args.model}, seeds={completed}; test remains locked.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"CAMPAIGN REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
