"""Download and forward-check every official backbone before campaign lock."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import torch
import torchvision

from benchmark_common import configure_utf8_console, load_locked_inputs
from model_factory import build_model, parameter_summary


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_v1.json"
REPORT = ROOT / "runs" / "preflight" / "model_smoke_latest.json"


def main() -> int:
    configure_utf8_console()
    inputs = load_locked_inputs(CONTRACT)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing the intended RTX 4050 smoke test")
    device = torch.device("cuda")
    height, width, channels = inputs.contract["training"]["input_shape"]
    dummy = torch.zeros((1, channels, height, width), dtype=torch.float32, device=device)
    results: list[dict[str, object]] = []
    for model_id in inputs.contract["models"]:
        bundle = build_model(
            model_id,
            len(inputs.canonical_classes),
            float(inputs.contract["training"]["dropout"]),
        )
        model = bundle.model.to(device).eval()
        with torch.inference_mode():
            output = model(dummy)
        expected_shape = (1, len(inputs.canonical_classes))
        if tuple(output.shape) != expected_shape:
            raise RuntimeError(f"{model_id} output shape {tuple(output.shape)} != {expected_shape}")
        if not bool(torch.isfinite(output).all()):
            raise RuntimeError(f"{model_id} produced non-finite logits")
        summary = {
            "model_id": model_id,
            "status": "passed",
            "weights_id": bundle.weights_id,
            "output_shape": list(output.shape),
            **parameter_summary(model),
        }
        results.append(summary)
        print(f"MODEL SMOKE PASSED: {model_id} -> {tuple(output.shape)}", flush=True)
        del model, bundle, output
        torch.cuda.empty_cache()
    payload = {
        "schema_version": "riceai-model-smoke/v1",
        "status": "passed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "cuda": torch.version.cuda,
        "device": torch.cuda.get_device_name(0),
        "contract_sha256": inputs.contract_sha256,
        "split_manifest_sha256": inputs.manifest_sha256,
        "models": results,
    }
    REPORT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ALL MODEL SMOKE TESTS PASSED: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
