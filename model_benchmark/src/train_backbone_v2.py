"""Version-2 entry point; preserves the locked v1 implementation unchanged."""

from __future__ import annotations

import sys
from pathlib import Path

import train_backbone as implementation


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sys.argv.extend(
        [
            "--contract",
            str(ROOT / "config" / "benchmark_contract_v2.json"),
            "--campaign-lock",
            str(ROOT / "config" / "campaign_lock_v2.json"),
            "--output-root",
            str(ROOT / "runs" / "training_v2"),
        ]
    )
    return implementation.main()


if __name__ == "__main__":
    raise SystemExit(main())
