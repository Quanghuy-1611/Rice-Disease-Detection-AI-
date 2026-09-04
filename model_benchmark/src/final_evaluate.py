"""One-shot final test evaluation for all six models and three seeds."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader

from benchmark_common import (
    ContractError,
    build_provenance,
    configure_utf8_console,
    load_locked_inputs,
    read_json,
    sha256_file,
    validate_campaign_lock,
)
from model_factory import build_model
from train_backbone import ManifestDataset, build_transforms, confusion_and_metrics, save_json


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config" / "benchmark_contract_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_v1.json"
TRAINING_ROOT = ROOT / "runs" / "training"
OUTPUT_ROOT = ROOT / "runs" / "final_test"
UNLOCK_PHRASE = "I_UNDERSTAND_TEST_IS_FINAL"
BOOTSTRAP_SAMPLES = 2000
BOOTSTRAP_SEED = 2026


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate every locked checkpoint on test exactly once.")
    parser.add_argument("--unlock-test", required=True, choices=(UNLOCK_PHRASE,))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args()


def detailed_metrics(y_true: np.ndarray, y_pred: np.ndarray, classes: tuple[str, ...]) -> dict[str, Any]:
    class_count = len(classes)
    summary = confusion_and_metrics(y_true.tolist(), y_pred.tolist(), class_count)
    matrix = np.asarray(summary["confusion_matrix"], dtype=np.int64)
    tp = np.diag(matrix).astype(np.float64)
    predicted = matrix.sum(axis=0).astype(np.float64)
    actual = matrix.sum(axis=1).astype(np.float64)
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted > 0)
    recall = np.divide(tp, actual, out=np.zeros_like(tp), where=actual > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(tp), where=(precision + recall) > 0)
    summary["per_class"] = [
        {
            "class_index": index,
            "class_name": label,
            "support": int(actual[index]),
            "precision": float(precision[index]),
            "recall": float(recall[index]),
            "f1": float(f1[index]),
        }
        for index, label in enumerate(classes)
    ]
    return summary


def macro_f1_from_matrices(matrices: np.ndarray) -> np.ndarray:
    tp = np.diagonal(matrices, axis1=1, axis2=2).astype(np.float64)
    predicted = matrices.sum(axis=1).astype(np.float64)
    actual = matrices.sum(axis=2).astype(np.float64)
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted > 0)
    recall = np.divide(tp, actual, out=np.zeros_like(tp), where=actual > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(tp), where=(precision + recall) > 0)
    return f1.mean(axis=1)


def bootstrap_macro_f1_ci(y_true: np.ndarray, y_pred: np.ndarray, class_count: int, seed: int) -> dict[str, Any]:
    cell = y_true * class_count + y_pred
    counts = np.bincount(cell, minlength=class_count * class_count)
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(len(y_true), counts / counts.sum(), size=BOOTSTRAP_SAMPLES)
    scores = macro_f1_from_matrices(draws.reshape(-1, class_count, class_count))
    return {
        "method": "nonparametric_paired_image_bootstrap_via_multinomial_cells",
        "samples": BOOTSTRAP_SAMPLES,
        "seed": seed,
        "lower": float(np.percentile(scores, 2.5)),
        "upper": float(np.percentile(scores, 97.5)),
    }


def paired_bootstrap_delta(
    y_true: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    class_count: int,
    seed: int,
) -> dict[str, Any]:
    joint_id = (y_true * class_count + pred_a) * class_count + pred_b
    counts = np.bincount(joint_id, minlength=class_count ** 3)
    nonzero = counts > 0
    probabilities = counts[nonzero] / counts.sum()
    categories = np.flatnonzero(nonzero)
    true_category = categories // (class_count * class_count)
    remainder = categories % (class_count * class_count)
    a_category = remainder // class_count
    b_category = remainder % class_count
    rng = np.random.default_rng(seed)
    deltas: list[np.ndarray] = []
    chunk_size = 100
    for start in range(0, BOOTSTRAP_SAMPLES, chunk_size):
        size = min(chunk_size, BOOTSTRAP_SAMPLES - start)
        draws = rng.multinomial(len(y_true), probabilities, size=size)
        matrices_a = np.zeros((size, class_count, class_count), dtype=np.int64)
        matrices_b = np.zeros_like(matrices_a)
        for row in range(size):
            np.add.at(matrices_a[row], (true_category, a_category), draws[row])
            np.add.at(matrices_b[row], (true_category, b_category), draws[row])
        deltas.append(macro_f1_from_matrices(matrices_a) - macro_f1_from_matrices(matrices_b))
    delta = np.concatenate(deltas)
    actual_a = detailed_metrics(y_true, pred_a, tuple(str(i) for i in range(class_count)))["macro_f1"]
    actual_b = detailed_metrics(y_true, pred_b, tuple(str(i) for i in range(class_count)))["macro_f1"]
    return {
        "metric": "macro_f1",
        "delta_definition": "first_model_minus_second_model",
        "observed_delta": actual_a - actual_b,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "bootstrap_seed": seed,
        "ci95_lower": float(np.percentile(delta, 2.5)),
        "ci95_upper": float(np.percentile(delta, 97.5)),
        "probability_delta_gt_zero": float(np.mean(delta > 0)),
    }


def validate_all_runs(inputs: Any, campaign_lock_sha: str) -> dict[tuple[str, int], Path]:
    checkpoints: dict[tuple[str, int], Path] = {}
    for model_id, seed in itertools.product(
        inputs.contract["training"]["models_to_train"],
        inputs.contract["training"]["training_seeds"],
    ):
        run_dir = TRAINING_ROOT / model_id / f"seed_{seed}"
        manifest_path = run_dir / "run_manifest.json"
        checkpoint_path = run_dir / "best_model.pt"
        if not manifest_path.is_file() or not checkpoint_path.is_file():
            raise ContractError(f"Missing completed run: {model_id} seed {seed}")
        manifest = read_json(manifest_path)
        if manifest.get("status") != "complete" or manifest.get("test_evaluated") is not False:
            raise ContractError(f"Run is not cleanly complete/test-locked: {model_id} seed {seed}")
        provenance = manifest.get("provenance", {})
        expected = {
            "contract_sha256": inputs.contract_sha256,
            "split_manifest_sha256": inputs.manifest_sha256,
            "model_id": model_id,
            "training_seed": seed,
            "campaign_lock_sha256": campaign_lock_sha,
        }
        for key, value in expected.items():
            if provenance.get(key) != value:
                raise ContractError(f"Run provenance mismatch {model_id} seed {seed}: {key}")
        if manifest.get("best_model_sha256") != sha256_file(checkpoint_path):
            raise ContractError(f"Checkpoint SHA mismatch: {model_id} seed {seed}")
        checkpoints[(model_id, seed)] = checkpoint_path
    return checkpoints


def infer(model: torch.nn.Module, loader: DataLoader[Any], device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    labels_all: list[np.ndarray] = []
    probabilities_all: list[np.ndarray] = []
    model.eval()
    with torch.inference_mode():
        for images, labels in loader:
            logits = model(images.to(device, non_blocking=True))
            probabilities_all.append(torch.softmax(logits, dim=1).cpu().numpy())
            labels_all.append(labels.numpy())
    return np.concatenate(labels_all), np.concatenate(probabilities_all)


def main() -> int:
    configure_utf8_console()
    args = parse_args()
    inputs = load_locked_inputs(CONTRACT)
    validate_campaign_lock(inputs, CAMPAIGN_LOCK)
    lock_sha = sha256_file(CAMPAIGN_LOCK)
    checkpoints = validate_all_runs(inputs, lock_sha)
    if OUTPUT_ROOT.exists():
        raise ContractError(f"Final test directory already exists; refusing a second opening: {OUTPUT_ROOT}")
    OUTPUT_ROOT.mkdir(parents=True)
    save_json(
        OUTPUT_ROOT / "test_open_audit.json",
        {
            "status": "opened",
            "opened_at_utc": datetime.now(timezone.utc).isoformat(),
            "unlock_phrase_confirmed": True,
            "provenance": build_provenance(inputs),
            "campaign_lock_sha256": lock_sha,
        },
    )

    selected = "cuda" if args.device == "auto" and torch.cuda.is_available() else "cpu" if args.device == "auto" else args.device
    if selected == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    device = torch.device(selected)
    with inputs.manifest_path.open("r", encoding="utf-8", newline="") as handle:
        test_rows = [row for row in csv.DictReader(handle) if row["split"] == "test"]
    _, validation_transform = build_transforms(inputs.contract)
    dataset = ManifestDataset(test_rows, inputs.dataset_root, validation_transform)
    loader = DataLoader(
        dataset,
        batch_size=int(inputs.contract["training"]["batch_size"]),
        shuffle=False,
        num_workers=args.workers,
        pin_memory=device.type == "cuda",
        persistent_workers=args.workers > 0,
    )
    prediction_cache: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
    rows_summary: list[dict[str, Any]] = []

    for run_index, ((model_id, seed), checkpoint_path) in enumerate(checkpoints.items()):
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        bundle = build_model(model_id, len(inputs.canonical_classes), float(inputs.contract["training"]["dropout"]), load_pretrained=False)
        bundle.model.load_state_dict(checkpoint["state_dict"], strict=True)
        model = bundle.model.to(device)
        y_true, probabilities = infer(model, loader, device)
        y_pred = probabilities.argmax(axis=1)
        prediction_cache[(model_id, seed)] = (y_true, y_pred)
        metrics = detailed_metrics(y_true, y_pred, inputs.canonical_classes)
        metrics["bootstrap_ci95_macro_f1"] = bootstrap_macro_f1_ci(
            y_true, y_pred, len(inputs.canonical_classes), BOOTSTRAP_SEED + run_index
        )
        run_output = OUTPUT_ROOT / model_id / f"seed_{seed}"
        run_output.mkdir(parents=True)
        save_json(run_output / "test_metrics.json", metrics)
        with (run_output / "test_predictions.csv").open("w", encoding="utf-8", newline="") as handle:
            fields = ["relative_path", "true_index", "true_label", "predicted_index", "predicted_label", "confidence"] + [
                f"probability_{label}" for label in inputs.canonical_classes
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for index, source in enumerate(test_rows):
                predicted = int(y_pred[index])
                row = {
                    "relative_path": source["relative_path"],
                    "true_index": int(y_true[index]),
                    "true_label": inputs.canonical_classes[int(y_true[index])],
                    "predicted_index": predicted,
                    "predicted_label": inputs.canonical_classes[predicted],
                    "confidence": float(probabilities[index, predicted]),
                }
                row.update({f"probability_{label}": float(probabilities[index, class_index]) for class_index, label in enumerate(inputs.canonical_classes)})
                writer.writerow(row)
        rows_summary.append(
            {
                "model_id": model_id,
                "seed": seed,
                "framework": "pytorch_torchvision",
                "result_origin": "new_locked_campaign",
                **{
                    key: metrics[key]
                    for key in ("accuracy", "macro_precision", "macro_recall", "macro_f1")
                },
            }
        )
        del model, checkpoint, probabilities
        if device.type == "cuda":
            torch.cuda.empty_cache()
        print(f"TEST EVALUATED: {model_id} seed {seed}")

    by_model: dict[str, Any] = {}
    for model_id in inputs.contract["models"]:
        model_rows = [row for row in rows_summary if row["model_id"] == model_id]
        by_model[model_id] = {}
        for metric in ("accuracy", "macro_precision", "macro_recall", "macro_f1"):
            values = np.asarray([row[metric] for row in model_rows], dtype=np.float64)
            by_model[model_id][metric] = {
                "mean": float(values.mean()),
                "sample_std": float(values.std(ddof=1)) if len(values) > 1 else None,
                "values_by_seed": {str(row["seed"]): row[metric] for row in model_rows},
            }

    paired: dict[str, Any] = {}
    anchor = "mobilenetv3large"
    for other_index, other in enumerate(
        model for model in inputs.contract["models"] if model != anchor
    ):
        key = f"{anchor}_minus_{other}"
        paired[key] = {}
        for seed_index, seed in enumerate(inputs.contract["training"]["training_seeds"]):
            y_true, pred_anchor = prediction_cache[(anchor, seed)]
            y_true_other, pred_other = prediction_cache[(other, seed)]
            if not np.array_equal(y_true, y_true_other):
                raise ContractError("Test target order differs between runs")
            paired[key][str(seed)] = paired_bootstrap_delta(
                y_true,
                pred_anchor,
                pred_other,
                len(inputs.canonical_classes),
                BOOTSTRAP_SEED + 1000 + other_index * 10 + seed_index,
            )

    save_json(
        OUTPUT_ROOT / "final_comparison.json",
        {
            "schema_version": "riceai-final-backbone-comparison/v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "test_sample_count": len(test_rows),
            "per_run": rows_summary,
            "aggregate_across_training_seeds": by_model,
            "paired_bootstrap_vs_mobilenetv3large": paired,
            "comparison_design": inputs.contract["comparison_design"],
            "interpretation_guardrails": [
                "Training-seed sample_std and test-image bootstrap CI measure different uncertainty sources.",
                "Image-level split is not a plant/field/session group split.",
                "Do not claim final superiority from one metric without per-class and uncertainty review.",
            ],
        },
    )
    audit_path = OUTPUT_ROOT / "test_open_audit.json"
    audit = read_json(audit_path)
    audit["status"] = "complete"
    audit["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    save_json(audit_path, audit)
    print(f"FINAL TEST COMPLETE: {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"FINAL EVALUATION REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
