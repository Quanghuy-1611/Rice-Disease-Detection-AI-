"""Version-2 one-shot test entry point; test remains unavailable during train."""

from __future__ import annotations

from pathlib import Path

import final_evaluate as implementation


ROOT = Path(__file__).resolve().parents[1]
implementation.CONTRACT = ROOT / "config" / "benchmark_contract_v2.json"
implementation.CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_v2.json"
implementation.TRAINING_ROOT = ROOT / "runs" / "training_v2"
implementation.OUTPUT_ROOT = ROOT / "runs" / "final_test_v2"


if __name__ == "__main__":
    raise SystemExit(implementation.main())
