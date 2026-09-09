"""Exercise real forward/backward steps for all backbones before campaign lock."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import torch
from torch import nn
from torch.optim import Adam
from torch.utils.data import DataLoader

from benchmark_common import configure_utf8_console, load_locked_inputs
from model_factory import build_model, configure_stage, keep_batchnorm_frozen
from train_backbone import (
    ManifestDataset,
    build_transforms,
    effective_class_weights,
    load_rows,
    seed_everything,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runs" / "preflight" / "training_smoke_latest.json"


def one_training_step(
    model: nn.Module,
    images: torch.Tensor,
    labels: torch.Tensor,
    criterion: nn.Module,
    learning_rate: float,
) -> float:
    optimizer = Adam((parameter for parameter in model.parameters() if parameter.requires_grad), lr=learning_rate)
    model.train()
    keep_batchnorm_frozen(model)
    optimizer.zero_grad(set_to_none=True)
    logits = model(images)
    if tuple(logits.shape) != (images.shape[0], int(model._riceai_class_count)):
        raise RuntimeError(f"Unexpected logits shape: {tuple(logits.shape)}")
    loss = criterion(logits, labels)
    if not bool(torch.isfinite(loss)):
        raise RuntimeError("Non-finite training loss")
    loss.backward()
    optimizer.step()
    return float(loss.detach())


def main() -> int:
    configure_utf8_console()
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    args = parser.parse_args()
    inputs = load_locked_inputs(args.contract)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    seed = int(inputs.contract["training"]["training_seeds"][0])
    seed_everything(seed)
    device = torch.device(args.device)
    rows = load_rows(inputs.manifest_path)
    train_transform, _ = build_transforms(inputs.contract)
    dataset = ManifestDataset(rows["train"], inputs.dataset_root, train_transform)
    loader = DataLoader(
        dataset,
        batch_size=int(inputs.contract["training"]["batch_size"]),
        shuffle=False,
        num_workers=0,
    )
    images, labels = next(iter(loader))
    images = images.to(device)
    labels = labels.to(device)
    weights = effective_class_weights(
        rows["train"],
        len(inputs.canonical_classes),
        inputs.contract["training"]["class_weighting"],
    ).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    results: list[dict[str, object]] = []

    for model_id in inputs.contract["models"]:
        if device.type == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(device)
        bundle = build_model(
            model_id,
            len(inputs.canonical_classes),
            float(inputs.contract["training"]["dropout"]),
        )
        model = bundle.model.to(device)
        model._riceai_class_count = len(inputs.canonical_classes)
        configure_stage(model, bundle.classifier_parameter_names, "head")
        head_loss = one_training_step(
            model,
            images,
            labels,
            criterion,
            float(inputs.contract["training"]["head_learning_rate"]),
        )
        configure_stage(model, bundle.classifier_parameter_names, "finetune")
        finetune_loss = one_training_step(
            model,
            images,
            labels,
            criterion,
            float(inputs.contract["training"]["fine_tune_learning_rate"]),
        )
        peak_mb = torch.cuda.max_memory_allocated(device) / (1024 ** 2) if device.type == "cuda" else 0.0
        result = {
            "model_id": model_id,
            "status": "passed",
            "batch_size": int(images.shape[0]),
            "head_loss": head_loss,
            "finetune_loss": finetune_loss,
            "peak_cuda_memory_allocated_mb": peak_mb,
        }
        results.append(result)
        print(
            f"TRAINING SMOKE PASSED: {model_id} "
            f"batch={images.shape[0]} peak_cuda={peak_mb:.1f} MB",
            flush=True,
        )
        del model, bundle
        if device.type == "cuda":
            torch.cuda.empty_cache()

    payload = {
        "schema_version": "riceai-training-smoke/v1",
        "status": "passed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": inputs.contract_sha256,
        "split_manifest_sha256": inputs.manifest_sha256,
        "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        "models": results,
    }
    REPORT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"ALL TRAINING SMOKE TESTS PASSED: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
