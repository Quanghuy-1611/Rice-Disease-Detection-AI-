"""Version-2 campaign entry point using the validation-revised epoch budget."""

from __future__ import annotations

from pathlib import Path

import run_campaign as implementation


ROOT = Path(__file__).resolve().parents[1]
implementation.CONTRACT = ROOT / "config" / "benchmark_contract_v2.json"
implementation.CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_v2.json"
implementation.TRAIN_SCRIPT = ROOT / "src" / "train_backbone_v2.py"
implementation.TRAINING_ROOT = ROOT / "runs" / "training_v2"
implementation.PROGRESS_PATH = ROOT / "runs" / "campaign_progress_v2.json"


if __name__ == "__main__":
    raise SystemExit(implementation.main())
