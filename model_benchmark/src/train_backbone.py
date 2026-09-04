"""Train one locked backbone/seed without reading test images.

The script intentionally has no --evaluate-test option. Final test evaluation is
implemented separately so tuning and test access cannot be mixed accidentally.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.transforms import InterpolationMode

from benchmark_common import (
    ContractError,
    build_provenance,
    configure_utf8_console,
    load_locked_inputs,
    sha256_file,
    validate_campaign_lock,
)
from model_factory import build_model, configure_stage, keep_batchnorm_frozen, parameter_summary


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "config" / "benchmark_contract_v1.json"
DEFAULT_CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_v1.json"


class ManifestDataset(Dataset[tuple[torch.Tensor, int]]):
    def __init__(self, rows: list[dict[str, str]], root: Path, transform: Any) -> None:
        self.rows = rows
        self.root = root.resolve()
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        row = self.rows[index]
        path = (self.root / row["relative_path"]).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise RuntimeError(f"Manifest path escaped dataset root: {row['relative_path']}") from exc
        with Image.open(path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, int(row["label_index"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train one backbone under the locked RiceAI protocol.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--campaign-lock", type=Path, default=DEFAULT_CAMPAIGN_LOCK)
    parser.add_argument("--output-root", type=Path, default=ROOT / "runs" / "training")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args()


def seed_everything(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    # Required by CUDA >= 10.2 for deterministic CuBLAS matrix operations.
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)


def load_rows(manifest: Path) -> dict[str, list[dict[str, str]]]:
    rows: dict[str, list[dict[str, str]]] = {"train": [], "validation": []}
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            # Test rows are intentionally not returned to the training pipeline.
            if row["split"] in rows:
                rows[row["split"]].append(row)
    return rows


def build_transforms(contract: dict[str, Any]) -> tuple[Any, Any]:
    training = contract["training"]
    implementation = contract["implementation"]
    augmentation = training["augmentation"]
    height, width, _ = training["input_shape"]
    normalize = transforms.Normalize(implementation["imagenet_mean"], implementation["imagenet_std"])
    common_tail = [transforms.ToTensor(), normalize]
    train_transform = transforms.Compose(
        [
            transforms.Resize((height, width), interpolation=InterpolationMode.BILINEAR, antialias=True),
            transforms.RandomHorizontalFlip(augmentation["horizontal_flip_probability"]),
            transforms.RandomAffine(
                degrees=augmentation["rotation_degrees"],
                translate=(augmentation["translation_fraction"], augmentation["translation_fraction"]),
                scale=tuple(augmentation["scale_range"]),
                interpolation=InterpolationMode.BILINEAR,
            ),
            transforms.ColorJitter(
                brightness=augmentation["brightness"],
                contrast=augmentation["contrast"],
            ),
            *common_tail,
        ]
    )
    validation_transform = transforms.Compose(
        [
            transforms.Resize((height, width), interpolation=InterpolationMode.BILINEAR, antialias=True),
            *common_tail,
        ]
    )
    return train_transform, validation_transform


def effective_class_weights(rows: list[dict[str, str]], class_count: int, config: dict[str, Any]) -> torch.Tensor:
    counts = np.zeros(class_count, dtype=np.int64)
    for row in rows:
        counts[int(row["label_index"])] += 1
    if np.any(counts == 0):
        raise ContractError("Train split has an empty class")
    beta = float(config["beta"])
    values = (1.0 - beta) / (1.0 - np.power(beta, counts.astype(np.float64)))
    values /= values.mean()
    values = np.clip(values, float(config["minimum"]), float(config["maximum"]))
    return torch.tensor(values, dtype=torch.float32)


def confusion_and_metrics(y_true: list[int], y_pred: list[int], class_count: int) -> dict[str, Any]:
    matrix = np.zeros((class_count, class_count), dtype=np.int64)
    np.add.at(matrix, (np.asarray(y_true), np.asarray(y_pred)), 1)
    tp = np.diag(matrix).astype(np.float64)
    predicted = matrix.sum(axis=0).astype(np.float64)
    actual = matrix.sum(axis=1).astype(np.float64)
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted > 0)
    recall = np.divide(tp, actual, out=np.zeros_like(tp), where=actual > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(tp), where=(precision + recall) > 0)
    return {
        "accuracy": float(tp.sum() / matrix.sum()),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1.mean()),
        "confusion_matrix": matrix.tolist(),
    }


def run_epoch(
    model: nn.Module,
    loader: DataLoader[Any],
    criterion: nn.Module,
    device: torch.device,
    optimizer: Adam | None,
) -> dict[str, Any]:
    training = optimizer is not None
    model.train(training)
    if training:
        keep_batchnorm_frozen(model)
    total_loss = 0.0
    total_examples = 0
    y_true: list[int] = []
    y_pred: list[int] = []
    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        if training:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(training):
            logits = model(images)
            loss = criterion(logits, labels)
            if training:
                loss.backward()
                optimizer.step()
        total_loss += float(loss.detach()) * labels.size(0)
        total_examples += labels.size(0)
        y_true.extend(labels.detach().cpu().tolist())
        y_pred.extend(logits.argmax(dim=1).detach().cpu().tolist())
    metrics = confusion_and_metrics(y_true, y_pred, int(model._riceai_class_count))
    metrics["loss"] = total_loss / total_examples
    return metrics


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_console()
    args = parse_args()
    inputs = load_locked_inputs(args.contract)
    campaign_lock = validate_campaign_lock(inputs, args.campaign_lock)
    contract = inputs.contract
    if args.model not in contract["training"]["models_to_train"]:
        raise ContractError(
            f"Model {args.model!r} is not in locked models_to_train: "
            f"{contract['training']['models_to_train']}"
        )
    if args.seed not in contract["training"]["training_seeds"]:
        raise ContractError(f"Seed {args.seed} is not in locked training_seeds")
    if args.workers < 0:
        raise ValueError("--workers must be >= 0")

    run_dir = (args.output_root / args.model / f"seed_{args.seed}").resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise RuntimeError(f"Run directory is not empty; refusing overwrite: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    seed_everything(args.seed)

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but CUDA is unavailable")
    selected_device = (
        "cuda" if args.device == "auto" and torch.cuda.is_available()
        else "cpu" if args.device == "auto"
        else args.device
    )
    device = torch.device(selected_device)

    rows = load_rows(inputs.manifest_path)
    train_transform, validation_transform = build_transforms(contract)
    train_dataset = ManifestDataset(rows["train"], inputs.dataset_root, train_transform)
    validation_dataset = ManifestDataset(rows["validation"], inputs.dataset_root, validation_transform)
    loader_args = {
        "batch_size": int(contract["training"]["batch_size"]),
        "num_workers": args.workers,
        "pin_memory": device.type == "cuda",
        "persistent_workers": args.workers > 0,
    }
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(train_dataset, shuffle=True, generator=generator, **loader_args)
    validation_loader = DataLoader(validation_dataset, shuffle=False, **loader_args)

    bundle = build_model(
        args.model,
        len(inputs.canonical_classes),
        float(contract["training"]["dropout"]),
    )
    model = bundle.model
    model._riceai_class_count = len(inputs.canonical_classes)
    model.to(device)
    class_weights = effective_class_weights(
        rows["train"], len(inputs.canonical_classes), contract["training"]["class_weighting"]
    ).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    provenance = {
        **build_provenance(inputs),
        "model_id": args.model,
        "training_seed": args.seed,
        "weights_id": bundle.weights_id,
        "device": str(device),
        "python": sys.version,
        "torch": torch.__version__,
        "torchvision": __import__("torchvision").__version__,
        "command": [sys.executable, *sys.argv],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "campaign_lock_sha256": sha256_file(args.campaign_lock.resolve()),
        "campaign_id": campaign_lock["campaign_id"],
    }
    save_json(run_dir / "run_manifest.json", {"status": "running", "provenance": provenance})

    best_f1 = -math.inf
    best_epoch = -1
    epochs_without_improvement = 0
    global_epoch = 0
    history: list[dict[str, Any]] = []
    started = time.perf_counter()
    training_config = contract["training"]

    for stage, epochs, learning_rate in (
        ("head", int(training_config["head_epochs"]), float(training_config["head_learning_rate"])),
        ("finetune", int(training_config["fine_tune_epochs"]), float(training_config["fine_tune_learning_rate"])),
    ):
        configure_stage(model, bundle.classifier_parameter_names, stage)
        optimizer = Adam((p for p in model.parameters() if p.requires_grad), lr=learning_rate)
        scheduler = ReduceLROnPlateau(
            optimizer,
            mode="max",
            factor=float(training_config["reduce_lr_factor"]),
            patience=max(1, int(training_config["early_stopping_patience"]) // 2),
            min_lr=float(training_config["reduce_lr_min"]),
        )
        epochs_without_improvement = 0
        for stage_epoch in range(1, epochs + 1):
            global_epoch += 1
            train_metrics = run_epoch(model, train_loader, criterion, device, optimizer)
            with torch.inference_mode():
                validation_metrics = run_epoch(model, validation_loader, criterion, device, None)
            scheduler.step(validation_metrics["macro_f1"])
            record = {
                "global_epoch": global_epoch,
                "stage": stage,
                "stage_epoch": stage_epoch,
                "learning_rate": float(optimizer.param_groups[0]["lr"]),
                "train": train_metrics,
                "validation": validation_metrics,
                "parameters": parameter_summary(model),
            }
            history.append(record)
            save_json(run_dir / "history.json", {"epochs": history})
            print(
                f"[{args.model} seed={args.seed}] {stage} {stage_epoch}/{epochs} "
                f"val_macro_f1={validation_metrics['macro_f1']:.6f}"
            )
            if validation_metrics["macro_f1"] > best_f1:
                best_f1 = validation_metrics["macro_f1"]
                best_epoch = global_epoch
                epochs_without_improvement = 0
                torch.save(
                    {
                        "model_id": args.model,
                        "class_names": list(inputs.canonical_classes),
                        "contract_sha256": inputs.contract_sha256,
                        "split_manifest_sha256": inputs.manifest_sha256,
                        "weights_id": bundle.weights_id,
                        "training_seed": args.seed,
                        "global_epoch": global_epoch,
                        "validation_metrics": validation_metrics,
                        "state_dict": model.state_dict(),
                    },
                    run_dir / "best_model.pt",
                )
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= int(training_config["early_stopping_patience"]):
                    print(f"Early stopping stage {stage} at epoch {stage_epoch}")
                    break

    checkpoint = run_dir / "best_model.pt"
    final_manifest = {
        "status": "complete",
        "provenance": provenance,
        "best_validation_macro_f1": best_f1,
        "best_global_epoch": best_epoch,
        "best_model_sha256": sha256_file(checkpoint),
        "duration_seconds": time.perf_counter() - started,
        "test_evaluated": False,
    }
    save_json(run_dir / "run_manifest.json", final_manifest)
    print(f"TRAINING COMPLETE: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
