"""Locked, one-shot final evaluation for the large 11-class campaign.

The script deliberately refuses to inspect either test split until every one of
the 18 training runs is complete and the validation-only architecture ranking
has been frozen in an evaluation lock.  Internal and external results are
written separately and must never be used to revise the trained campaign.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
from collections import Counter
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
from train_backbone import ManifestDataset, build_transforms, save_json


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
CONTRACT = ROOT / "config" / "benchmark_contract_11class_large_v1.json"
CAMPAIGN_LOCK = ROOT / "config" / "campaign_lock_11class_large_v1.json"
DATASET_LOCK = PROJECT / "research" / "locks" / "dataset_11_large_v1.lock.json"
SELECTION_MANIFEST = PROJECT / "research" / "audit_11class_large_v1" / "selected_large_manifest_v1.csv"
EXTERNAL_ROOT = PROJECT / "research" / "external_test_11class"
EXTERNAL_MANIFEST = PROJECT / "research" / "external_test_11class_manifest_v1.csv"
EXTERNAL_LOCK = PROJECT / "research" / "external_test_11class_lock_v1.json"
CAMPAIGN_STATUS = ROOT / "runs" / "campaign_progress_11class_large_v1.json"
TRAINING_ROOT = ROOT / "runs" / "training_11class_large_v1"
OUTPUT_ROOT = ROOT / "runs" / "final_evaluation_11class_large_v1"
UNLOCK_PHRASE = "I_UNDERSTAND_TEST_IS_FINAL"
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 2026
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="One-shot internal and external evaluation after 18 locked runs.")
    parser.add_argument("--unlock-test", required=True, choices=(UNLOCK_PHRASE,))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args()


def sha256_rows(rows: list[dict[str, str]], path_key: str, sha_key: str) -> str:
    lines = [f"{row[path_key]}\0{row[sha_key]}\n" for row in rows]
    return hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_runs(inputs: Any, campaign_lock_sha: str) -> tuple[dict[tuple[str, int], Path], list[dict[str, Any]]]:
    checkpoints: dict[tuple[str, int], Path] = {}
    validation_rows: list[dict[str, Any]] = []
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
            raise ContractError(f"Run is not complete and test-locked: {model_id} seed {seed}")
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
        checkpoint_sha = sha256_file(checkpoint_path)
        if manifest.get("best_model_sha256") != checkpoint_sha:
            raise ContractError(f"Checkpoint SHA mismatch: {model_id} seed {seed}")
        checkpoints[(model_id, int(seed))] = checkpoint_path
        validation_rows.append({
            "model_id": model_id,
            "seed": int(seed),
            "best_validation_macro_f1": float(manifest["best_validation_macro_f1"]),
            "best_global_epoch": int(manifest["best_global_epoch"]),
            "checkpoint_sha256": checkpoint_sha,
        })
    return checkpoints, validation_rows


def validation_ranking(inputs: Any, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for order, model_id in enumerate(inputs.contract["training"]["models_to_train"]):
        values = np.asarray(
            [row["best_validation_macro_f1"] for row in rows if row["model_id"] == model_id],
            dtype=np.float64,
        )
        if len(values) != len(inputs.contract["training"]["training_seeds"]):
            raise ContractError(f"Incomplete validation values: {model_id}")
        ranked.append({
            "model_id": model_id,
            "validation_macro_f1_mean": float(values.mean()),
            "validation_macro_f1_sample_std": float(values.std(ddof=1)),
            "model_order_tiebreak": order,
        })
    ranked.sort(key=lambda row: (-row["validation_macro_f1_mean"], row["validation_macro_f1_sample_std"], row["model_order_tiebreak"]))
    for rank, row in enumerate(ranked, 1):
        row["validation_rank"] = rank
    return ranked


def validate_data_locks(campaign_lock: dict[str, Any]) -> dict[str, Any]:
    dataset_lock = read_json(DATASET_LOCK)
    external_lock = read_json(EXTERNAL_LOCK)
    if sha256_file(DATASET_LOCK) != campaign_lock.get("dataset_lock_sha256"):
        raise ContractError("Dataset lock changed after campaign lock")
    if sha256_file(EXTERNAL_LOCK) != campaign_lock.get("external_test_lock_sha256"):
        raise ContractError("External-test lock changed after campaign lock")
    if sha256_file(EXTERNAL_MANIFEST) != campaign_lock.get("external_test_manifest_sha256"):
        raise ContractError("External-test manifest changed after campaign lock")
    if dataset_lock.get("technical_integrity_passed") is not True:
        raise ContractError("Dataset lock did not pass technical integrity")
    if external_lock.get("status") != "locked" or external_lock.get("image_count") != 1100:
        raise ContractError("External-test lock is invalid")
    if sha256_file(EXTERNAL_MANIFEST) != external_lock.get("manifest_sha256"):
        raise ContractError("External manifest SHA differs from external lock")
    return {"dataset_lock": dataset_lock, "external_lock": external_lock}


def leakage_audit() -> dict[str, Any]:
    selected = read_csv(SELECTION_MANIFEST)
    external = read_csv(EXTERNAL_MANIFEST)
    train_sha = {row["sha256"] for row in selected}
    train_pixel = {row["pixel_sha256"] for row in selected}
    train_phash = [int(row["phash"], 16) for row in selected]
    external_sha = [row["sha256"] for row in external]
    external_pixel = [row["pixel_sha256"] for row in external]
    external_phash = [int(row["canonical_phash64"], 16) for row in external]
    exact_overlap = sorted(train_sha.intersection(external_sha))
    pixel_overlap = sorted(train_pixel.intersection(external_pixel))
    minimum_distances = [min((value ^ other).bit_count() for other in train_phash) for value in external_phash]
    near_count = sum(distance <= 8 for distance in minimum_distances)
    duplicate_external_sha = len(external_sha) - len(set(external_sha))
    duplicate_external_pixel = len(external_pixel) - len(set(external_pixel))
    result = {
        "training_selection_count": len(selected),
        "external_count": len(external),
        "exact_sha_overlap_count": len(exact_overlap),
        "decoded_pixel_overlap_count": len(pixel_overlap),
        "external_phash_hamming_le_8_count": near_count,
        "minimum_external_to_training_phash_distance": min(minimum_distances),
        "duplicate_external_sha_count": duplicate_external_sha,
        "duplicate_external_pixel_count": duplicate_external_pixel,
        "passed": not exact_overlap and not pixel_overlap and near_count == 0 and duplicate_external_sha == 0 and duplicate_external_pixel == 0,
    }
    if not result["passed"]:
        raise ContractError(f"External leakage audit failed: {result}")
    return result


def verify_rows(root: Path, rows: list[dict[str, str]]) -> None:
    resolved_root = root.resolve()
    for index, row in enumerate(rows, 1):
        path = (resolved_root / row["relative_path"]).resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError as exc:
            raise ContractError(f"Unsafe test path: {row['relative_path']}") from exc
        if not path.is_file() or sha256_file(path) != row["sha256"]:
            raise ContractError(f"Missing or modified test image: {row['relative_path']}")
        if index % 500 == 0:
            print(f"Verified test images: {index}/{len(rows)}", flush=True)


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, class_count: int) -> np.ndarray:
    matrix = np.zeros((class_count, class_count), dtype=np.int64)
    np.add.at(matrix, (y_true, y_pred), 1)
    return matrix


def metrics_from_matrix(matrix: np.ndarray) -> dict[str, Any]:
    tp = np.diag(matrix).astype(np.float64)
    predicted = matrix.sum(axis=0).astype(np.float64)
    actual = matrix.sum(axis=1).astype(np.float64)
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted > 0)
    recall = np.divide(tp, actual, out=np.zeros_like(tp), where=actual > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(tp), where=(precision + recall) > 0)
    return {
        "accuracy": float(tp.sum() / matrix.sum()),
        "balanced_accuracy": float(recall.mean()),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1.mean()),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": actual.astype(np.int64),
    }


def ece(probabilities: np.ndarray, y_true: np.ndarray, bins: int = 15) -> float:
    confidence = probabilities.max(axis=1)
    correct = probabilities.argmax(axis=1) == y_true
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for index in range(bins):
        mask = (confidence > edges[index]) & (confidence <= edges[index + 1])
        if index == 0:
            mask |= confidence == 0.0
        if mask.any():
            total += float(mask.mean()) * abs(float(correct[mask].mean()) - float(confidence[mask].mean()))
    return total


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = (p + z * z / (2.0 * total)) / denominator
    radius = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denominator
    return max(0.0, centre - radius), min(1.0, centre + radius)


def stratified_bootstrap_ci(matrix: np.ndarray, seed: int) -> dict[str, Any]:
    class_count = matrix.shape[0]
    rng = np.random.default_rng(seed)
    draws = np.zeros((BOOTSTRAP_SAMPLES, class_count, class_count), dtype=np.int32)
    for label in range(class_count):
        count = int(matrix[label].sum())
        draws[:, label, :] = rng.multinomial(count, matrix[label] / count, size=BOOTSTRAP_SAMPLES)
    tp = np.diagonal(draws, axis1=1, axis2=2).astype(np.float64)
    predicted = draws.sum(axis=1).astype(np.float64)
    actual = draws.sum(axis=2).astype(np.float64)
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted > 0)
    recall = np.divide(tp, actual, out=np.zeros_like(tp), where=actual > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(tp), where=(precision + recall) > 0)
    macro_f1 = f1.mean(axis=1)
    accuracy = tp.sum(axis=1) / draws.sum(axis=(1, 2))
    return {
        "method": "class_stratified_nonparametric_percentile_bootstrap",
        "samples": BOOTSTRAP_SAMPLES,
        "seed": seed,
        "macro_f1": {"lower": float(np.percentile(macro_f1, 2.5)), "upper": float(np.percentile(macro_f1, 97.5))},
        "accuracy": {"lower": float(np.percentile(accuracy, 2.5)), "upper": float(np.percentile(accuracy, 97.5))},
    }


def detailed_metrics(y_true: np.ndarray, probabilities: np.ndarray, classes: tuple[str, ...], seed: int) -> dict[str, Any]:
    y_pred = probabilities.argmax(axis=1)
    matrix = confusion_matrix(y_true, y_pred, len(classes))
    base = metrics_from_matrix(matrix)
    one_hot = np.eye(len(classes), dtype=np.float64)[y_true]
    chosen = np.clip(probabilities[np.arange(len(y_true)), y_true], 1e-15, 1.0)
    top2 = np.argpartition(probabilities, -2, axis=1)[:, -2:]
    per_class = []
    for index, label in enumerate(classes):
        successes = int(matrix[index, index])
        support = int(base["support"][index])
        low, high = wilson_interval(successes, support)
        per_class.append({
            "class_index": index,
            "class_name": label,
            "support": support,
            "precision": float(base["precision"][index]),
            "recall": float(base["recall"][index]),
            "recall_wilson_ci95": {"lower": low, "upper": high},
            "f1": float(base["f1"][index]),
        })
    return {
        **{key: base[key] for key in ("accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1")},
        "top2_accuracy": float(np.mean(np.any(top2 == y_true[:, None], axis=1))),
        "negative_log_likelihood": float(-np.log(chosen).mean()),
        "multiclass_brier_score": float(np.square(probabilities - one_hot).sum(axis=1).mean()),
        "ece_15_bins": ece(probabilities, y_true, 15),
        "confusion_matrix": matrix.tolist(),
        "per_class": per_class,
        "bootstrap_ci95": stratified_bootstrap_ci(matrix, seed),
    }


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


def write_predictions(path: Path, rows: list[dict[str, str]], y_true: np.ndarray, probabilities: np.ndarray, classes: tuple[str, ...]) -> None:
    y_pred = probabilities.argmax(axis=1)
    fields = ["relative_path", "true_index", "true_label", "predicted_index", "predicted_label", "confidence"] + [
        f"probability_{label}" for label in classes
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, source in enumerate(rows):
            predicted = int(y_pred[index])
            item: dict[str, Any] = {
                "relative_path": source["relative_path"],
                "true_index": int(y_true[index]),
                "true_label": classes[int(y_true[index])],
                "predicted_index": predicted,
                "predicted_label": classes[predicted],
                "confidence": float(probabilities[index, predicted]),
            }
            item.update({f"probability_{label}": float(probabilities[index, class_index]) for class_index, label in enumerate(classes)})
            writer.writerow(item)


def aggregate_runs(models: list[str], seeds: list[int], metrics: dict[tuple[str, int], dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    fields = ("accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1", "top2_accuracy", "negative_log_likelihood", "multiclass_brier_score", "ece_15_bins")
    for model_id in models:
        output[model_id] = {}
        for field in fields:
            values = np.asarray([metrics[(model_id, seed)][field] for seed in seeds], dtype=np.float64)
            output[model_id][field] = {
                "mean": float(values.mean()),
                "sample_std": float(values.std(ddof=1)),
                "values_by_seed": {str(seed): float(metrics[(model_id, seed)][field]) for seed in seeds},
            }
    return output


def exact_mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [1.0] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def mcnemar_comparisons(anchor: str, models: list[str], seeds: list[int], predictions: dict[tuple[str, int], np.ndarray], y_true: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for other in models:
        if other == anchor:
            continue
        for seed in seeds:
            correct_a = predictions[(anchor, seed)] == y_true
            correct_b = predictions[(other, seed)] == y_true
            b = int(np.sum(correct_a & ~correct_b))
            c = int(np.sum(~correct_a & correct_b))
            rows.append({
                "anchor": anchor,
                "other": other,
                "seed": seed,
                "anchor_correct_other_wrong": b,
                "anchor_wrong_other_correct": c,
                "exact_mcnemar_p_unadjusted": exact_mcnemar_p(b, c),
            })
    adjusted = holm_adjust([row["exact_mcnemar_p_unadjusted"] for row in rows])
    for row, value in zip(rows, adjusted):
        row["holm_adjusted_p_family_15"] = value
        row["reject_equal_error_rate_at_0_05"] = value < 0.05
    return rows


def main() -> int:
    configure_utf8_console()
    args = parse_args()
    if args.workers < 0:
        raise ContractError("--workers must be >= 0")
    inputs = load_locked_inputs(CONTRACT)
    campaign_lock = validate_campaign_lock(inputs, CAMPAIGN_LOCK)
    campaign_lock_sha = sha256_file(CAMPAIGN_LOCK)
    campaign_status = read_json(CAMPAIGN_STATUS)
    if campaign_status.get("status") != "complete":
        raise ContractError("Campaign is not complete; refusing to open test data")
    checkpoints, validation_rows = validate_runs(inputs, campaign_lock_sha)
    ranking = validation_ranking(inputs, validation_rows)
    selected_model = ranking[0]["model_id"]
    lock_details = validate_data_locks(campaign_lock)
    leakage = leakage_audit()
    if OUTPUT_ROOT.exists():
        raise ContractError(f"Final evaluation already opened; refusing overwrite: {OUTPUT_ROOT}")

    # Freeze every selection decision before reading a single test image.
    OUTPUT_ROOT.mkdir(parents=True)
    evaluation_lock = {
        "schema_version": "riceai-final-evaluation-lock/v1",
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_rule": "highest_mean_validation_macro_f1_across_three_seeds; lower_sample_sd_then_contract_order_tiebreak",
        "selected_model": selected_model,
        "validation_ranking": ranking,
        "validation_runs": validation_rows,
        "contract_sha256": inputs.contract_sha256,
        "campaign_lock_sha256": campaign_lock_sha,
        "dataset_lock_sha256": sha256_file(DATASET_LOCK),
        "external_test_lock_sha256": sha256_file(EXTERNAL_LOCK),
        "external_test_manifest_sha256": sha256_file(EXTERNAL_MANIFEST),
        "leakage_audit_before_test_open": leakage,
        "bootstrap_policy": {"method": "class_stratified_nonparametric_percentile", "samples": BOOTSTRAP_SAMPLES, "confidence": 0.95},
        "comparison_policy": "exact_McNemar_on_paired_correctness_per_seed_with_Holm_FWER_across_15_anchor_comparisons",
        "test_results_must_not_change_model_selection": True,
    }
    save_json(OUTPUT_ROOT / "evaluation_lock.json", evaluation_lock)

    selected_device = "cuda" if args.device == "auto" and torch.cuda.is_available() else "cpu" if args.device == "auto" else args.device
    if selected_device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    device = torch.device(selected_device)
    classes = inputs.canonical_classes
    models = list(inputs.contract["training"]["models_to_train"])
    seeds = [int(seed) for seed in inputs.contract["training"]["training_seeds"]]
    _, test_transform = build_transforms(inputs.contract)

    internal_rows = [row for row in read_csv(inputs.manifest_path) if row["split"] == "test"]
    external_raw = read_csv(EXTERNAL_MANIFEST)
    external_rows = []
    counts: Counter[str] = Counter()
    for row in external_raw:
        label = row["label"]
        if label not in classes:
            raise ContractError(f"Unknown external label: {label}")
        counts[label] += 1
        external_rows.append({
            "relative_path": row["locked_relative_path"],
            "label": label,
            "label_index": str(classes.index(label)),
            "sha256": row["sha256"],
        })
    if set(counts) != set(classes) or set(counts.values()) != {100}:
        raise ContractError(f"External test is not 11 x 100 balanced: {dict(counts)}")
    if sha256_rows(external_raw, "locked_relative_path", "sha256") != lock_details["external_lock"]["dataset_content_sha256"]:
        raise ContractError("External dataset content digest differs from lock")

    verify_rows(inputs.dataset_root, internal_rows)
    verify_rows(EXTERNAL_ROOT, external_rows)
    test_sets = {
        "internal_grouped_test": (inputs.dataset_root, internal_rows),
        "external_source_test": (EXTERNAL_ROOT, external_rows),
    }
    all_summary: dict[str, Any] = {}
    for set_index, (set_name, (data_root, rows)) in enumerate(test_sets.items()):
        dataset = ManifestDataset(rows, data_root, test_transform)
        loader = DataLoader(
            dataset,
            batch_size=int(inputs.contract["training"]["batch_size"]),
            shuffle=False,
            num_workers=args.workers,
            pin_memory=device.type == "cuda",
            persistent_workers=args.workers > 0,
        )
        run_metrics: dict[tuple[str, int], dict[str, Any]] = {}
        predictions: dict[tuple[str, int], np.ndarray] = {}
        probabilities_by_model: dict[str, list[np.ndarray]] = {model: [] for model in models}
        canonical_y_true: np.ndarray | None = None
        for run_index, (model_id, seed) in enumerate(itertools.product(models, seeds)):
            checkpoint = torch.load(checkpoints[(model_id, seed)], map_location="cpu", weights_only=False)
            bundle = build_model(model_id, len(classes), float(inputs.contract["training"]["dropout"]), load_pretrained=False)
            bundle.model.load_state_dict(checkpoint["state_dict"], strict=True)
            model = bundle.model.to(device)
            y_true, probabilities = infer(model, loader, device)
            if canonical_y_true is None:
                canonical_y_true = y_true
            elif not np.array_equal(canonical_y_true, y_true):
                raise ContractError("Test target order changed between runs")
            metrics = detailed_metrics(y_true, probabilities, classes, BOOTSTRAP_SEED + set_index * 100 + run_index)
            run_metrics[(model_id, seed)] = metrics
            predictions[(model_id, seed)] = probabilities.argmax(axis=1)
            probabilities_by_model[model_id].append(probabilities)
            run_output = OUTPUT_ROOT / set_name / model_id / f"seed_{seed}"
            run_output.mkdir(parents=True)
            save_json(run_output / "metrics.json", metrics)
            write_predictions(run_output / "predictions.csv", rows, y_true, probabilities, classes)
            del model, checkpoint
            if device.type == "cuda":
                torch.cuda.empty_cache()
            print(f"EVALUATED {set_name}: {model_id} seed {seed}", flush=True)
        assert canonical_y_true is not None
        aggregate = aggregate_runs(models, seeds, run_metrics)
        ensemble_probabilities = np.mean(np.stack(probabilities_by_model[selected_model]), axis=0)
        ensemble_metrics = detailed_metrics(
            canonical_y_true,
            ensemble_probabilities,
            classes,
            BOOTSTRAP_SEED + set_index * 100 + 99,
        )
        ensemble_dir = OUTPUT_ROOT / set_name / "selected_three_seed_probability_ensemble"
        ensemble_dir.mkdir(parents=True)
        save_json(ensemble_dir / "metrics.json", ensemble_metrics)
        write_predictions(ensemble_dir / "predictions.csv", rows, canonical_y_true, ensemble_probabilities, classes)
        comparisons = mcnemar_comparisons(selected_model, models, seeds, predictions, canonical_y_true)
        set_summary = {
            "sample_count": len(rows),
            "class_counts": dict(sorted(Counter(row["label"] for row in rows).items())),
            "selected_model_frozen_before_test": selected_model,
            "aggregate_across_training_seeds": aggregate,
            "selected_model_three_seed_probability_ensemble": ensemble_metrics,
            "paired_exact_mcnemar_with_holm": comparisons,
            "guardrails": [
                "Test rankings are descriptive and cannot revise validation-only model selection.",
                "Sample SD across three training seeds is descriptive; no t-test is performed on n=3 seeds.",
                "Bootstrap conditions on observed class counts and assumes test images are independent within class.",
                "ECE depends on binning and is descriptive; NLL and multiclass Brier are also reported.",
            ],
        }
        save_json(OUTPUT_ROOT / set_name / "summary.json", set_summary)
        all_summary[set_name] = set_summary

    audit = {
        "schema_version": "riceai-final-evaluation/v1",
        "status": "complete",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_model": selected_model,
        "provenance": build_provenance(inputs),
        "evaluation_lock_sha256": sha256_file(OUTPUT_ROOT / "evaluation_lock.json"),
        "internal_and_external_reported_separately": True,
        "external_test_used_for_retraining_or_selection": False,
        "results": all_summary,
    }
    save_json(OUTPUT_ROOT / "final_summary.json", audit)
    print(f"FINAL EVALUATION COMPLETE: {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"FINAL EVALUATION REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
