"""Run or resume one model across all seeds in the locked large-data campaign."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark_common import ContractError, configure_utf8_console, load_locked_inputs, read_json, validate_campaign_lock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_11class_large_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_11class_large_v1.json"
TRAIN_SCRIPT = ROOT / "src" / "train_backbone.py"
TRAINING_ROOT = ROOT / "runs" / "training_11class_large_v1"
INTERRUPTED_ROOT = ROOT / "runs" / "interrupted_11class_large_v1"


def is_complete(run_dir: Path) -> bool:
    manifest = run_dir / "run_manifest.json"
    checkpoint = run_dir / "best_model.pt"
    if not manifest.is_file() or not checkpoint.is_file():
        return False
    return read_json(manifest).get("status") == "complete"


def main() -> int:
    configure_utf8_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    inputs = load_locked_inputs(CONTRACT)
    validate_campaign_lock(inputs, CAMPAIGN_LOCK)
    models = list(inputs.contract["training"]["models_to_train"])
    seeds = [int(seed) for seed in inputs.contract["training"]["training_seeds"]]
    if args.model not in models:
        raise ContractError(f"Unknown locked model: {args.model}")

    for position, seed in enumerate(seeds, 1):
        run_dir = TRAINING_ROOT / args.model / f"seed_{seed}"
        if is_complete(run_dir):
            print(f"SKIP COMPLETE [{position}/{len(seeds)}]: {args.model}/seed_{seed}", flush=True)
            continue
        if run_dir.exists() and any(run_dir.iterdir()):
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            archive = INTERRUPTED_ROOT / args.model / f"seed_{seed}_{stamp}"
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(run_dir), str(archive))
            print(f"ARCHIVED PARTIAL RUN: {archive}", flush=True)
        command = [
            sys.executable, str(TRAIN_SCRIPT), "--model", args.model, "--seed", str(seed),
            "--workers", str(args.workers), "--device", args.device,
            "--contract", str(CONTRACT), "--campaign-lock", str(CAMPAIGN_LOCK),
            "--output-root", str(TRAINING_ROOT),
        ]
        print(f"START [{position}/{len(seeds)}]: {args.model}/seed_{seed}", flush=True)
        result = subprocess.run(command, cwd=ROOT.parent, check=False)
        if result.returncode != 0 or not is_complete(run_dir):
            raise RuntimeError(f"Training failed: {args.model}/seed_{seed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, RuntimeError) as exc:
        print(f"LARGE CAMPAIGN STOPPED: {exc}", file=sys.stderr)
        raise SystemExit(2)
