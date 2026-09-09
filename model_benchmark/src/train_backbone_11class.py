"""Guarded entry point for the 11-class campaign.

This file intentionally refuses to train until the contract release gates have
been cleared and a dedicated campaign lock exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from benchmark_common import ContractError, load_locked_inputs


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_11class_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_11class_v1.json"
OUTPUT_ROOT = ROOT / "runs" / "training_11class_v1"


def main() -> int:
    # Validate data/metadata before checking the release gate. Otherwise a closed
    # gate can conceal malformed inputs until the expensive campaign starts.
    try:
        inputs = load_locked_inputs(CONTRACT)
    except ContractError as exc:
        raise SystemExit(f"TRAINING BLOCKED: invalid benchmark inputs: {exc}") from exc
    contract = inputs.contract
    gates = contract.get("release_gates", {})
    if gates.get("training_allowed") is not True:
        pending = [name for name, value in gates.items() if value == "pending"]
        raise SystemExit(
            "TRAINING BLOCKED by benchmark_contract_11class_v1.json. "
            f"Pending release gates: {', '.join(pending) or 'unspecified'}"
        )
    if not CAMPAIGN_LOCK.is_file():
        raise SystemExit(f"TRAINING BLOCKED: missing campaign lock: {CAMPAIGN_LOCK}")
    import train_backbone as implementation
    sys.argv.extend([
        "--contract", str(CONTRACT),
        "--campaign-lock", str(CAMPAIGN_LOCK),
        "--output-root", str(OUTPUT_ROOT),
    ])
    return implementation.main()


if __name__ == "__main__":
    raise SystemExit(main())
