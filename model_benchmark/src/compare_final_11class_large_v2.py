"""Paired Macro-F1 inference for the locked 11-class final evaluation."""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

import numpy as np

from benchmark_common import ContractError, configure_utf8_console, read_json, sha256_file
from train_backbone import save_json


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "runs" / "final_evaluation_11class_large_v1"
EVALUATION_LOCK = OUTPUT_ROOT / "evaluation_lock.json"
FINAL_SUMMARY = OUTPUT_ROOT / "final_summary.json"
MODELS = ["mobilenetv2", "mobilenetv3large", "resnet18", "efficientnetb0", "shufflenetv2_1_0x", "densenet121"]
SEEDS = [42, 123, 2026]
TEST_SETS = ["internal_grouped_test", "external_source_test"]
RESAMPLES = 10_000
RNG_SEED = 92_026


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def confusion(y_true: np.ndarray, y_pred: np.ndarray, class_count: int) -> np.ndarray:
    matrix = np.zeros((class_count, class_count), dtype=np.int64)
    np.add.at(matrix, (y_true, y_pred), 1)
    return matrix


def macro_f1_many(matrices: np.ndarray) -> np.ndarray:
    tp = np.diagonal(matrices, axis1=1, axis2=2).astype(np.float64)
    predicted = matrices.sum(axis=1).astype(np.float64)
    actual = matrices.sum(axis=2).astype(np.float64)
    precision = np.divide(tp, predicted, out=np.zeros_like(tp), where=predicted > 0)
    recall = np.divide(tp, actual, out=np.zeros_like(tp), where=actual > 0)
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(tp),
        where=(precision + recall) > 0,
    )
    return f1.mean(axis=1)


def macro_f1(matrix: np.ndarray) -> float:
    return float(macro_f1_many(matrix[None, :, :])[0])


def paired_inference(
    y_true: np.ndarray,
    pred_anchor: np.ndarray,
    pred_other: np.ndarray,
    class_count: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    boot_anchor = np.zeros((RESAMPLES, class_count, class_count), dtype=np.int32)
    boot_other = np.zeros_like(boot_anchor)
    null_anchor = np.zeros_like(boot_anchor)
    null_other = np.zeros_like(boot_anchor)
    for true_label in range(class_count):
        mask = y_true == true_label
        sample_count = int(mask.sum())
        if sample_count == 0:
            raise ContractError(f"Test set has no examples for class index {true_label}")
        joint_id = pred_anchor[mask] * class_count + pred_other[mask]
        counts = np.bincount(
            joint_id, minlength=class_count * class_count
        ).reshape(class_count, class_count)
        bootstrap = rng.multinomial(
            sample_count,
            counts.reshape(-1) / sample_count,
            size=RESAMPLES,
        ).reshape(RESAMPLES, class_count, class_count)
        boot_anchor[:, true_label, :] = bootstrap.sum(axis=2)
        boot_other[:, true_label, :] = bootstrap.sum(axis=1)
        for anchor_label, other_label in zip(*np.nonzero(counts)):
            count = int(counts[anchor_label, other_label])
            swapped = rng.binomial(count, 0.5, size=RESAMPLES)
            not_swapped = count - swapped
            null_anchor[:, true_label, anchor_label] += not_swapped
            null_anchor[:, true_label, other_label] += swapped
            null_other[:, true_label, other_label] += not_swapped
            null_other[:, true_label, anchor_label] += swapped
    observed = (
        macro_f1(confusion(y_true, pred_anchor, class_count))
        - macro_f1(confusion(y_true, pred_other, class_count))
    )
    bootstrap_delta = macro_f1_many(boot_anchor) - macro_f1_many(boot_other)
    null_delta = macro_f1_many(null_anchor) - macro_f1_many(null_other)
    p_value = (
        1.0 + float(np.sum(np.abs(null_delta) >= abs(observed)))
    ) / (RESAMPLES + 1.0)
    lower = float(np.percentile(bootstrap_delta, 2.5))
    upper = float(np.percentile(bootstrap_delta, 97.5))
    return {
        "metric": "macro_f1",
        "delta_definition": "validation_selected_anchor_minus_other",
        "observed_delta": observed,
        "paired_class_stratified_bootstrap": {
            "resamples": RESAMPLES,
            "ci95_percentile_lower": lower,
            "ci95_percentile_upper": upper,
            "ci95_excludes_zero": bool(lower > 0.0 or upper < 0.0),
        },
        "paired_randomization_test": {
            "null": "predictions_are_exchangeable_within_each_test_image",
            "resamples": RESAMPLES,
            "two_sided_monte_carlo_p_unadjusted": p_value,
        },
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [1.0] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def main() -> int:
    configure_utf8_console()
    if not EVALUATION_LOCK.is_file() or not FINAL_SUMMARY.is_file():
        raise ContractError("Final evaluation is not complete; paired comparison refused")
    lock = read_json(EVALUATION_LOCK)
    summary = read_json(FINAL_SUMMARY)
    if summary.get("status") != "complete":
        raise ContractError("Final evaluation summary is not complete")
    if summary.get("evaluation_lock_sha256") != sha256_file(EVALUATION_LOCK):
        raise ContractError("Evaluation lock SHA mismatch")
    anchor = lock.get("selected_model")
    if anchor not in MODELS or summary.get("selected_model") != anchor:
        raise ContractError("Frozen validation-selected model mismatch")
    class_count = int(summary["provenance"]["class_count"])
    final: dict[str, Any] = {
        "schema_version": "riceai-paired-final-comparison/v1",
        "selection_anchor_frozen_before_test": anchor,
        "metric": "macro_f1",
        "resampling_unit": "test_image_paired_between_models",
        "stratification": "true_class_fixed_at_observed_support",
        "resamples": RESAMPLES,
        "test_sets": {},
        "guardrails": [
            "Holm adjustment controls family-wise error across 15 anchor comparisons within each test set.",
            "Bootstrap CI quantifies finite test-image uncertainty conditional on trained checkpoints.",
            "Training-seed variability is separately reported as mean and sample SD; n=3 is not used for a t-test.",
            "Test results cannot revise the validation-only architecture selection.",
        ],
    }
    for set_index, test_set in enumerate(TEST_SETS):
        comparisons: list[dict[str, Any]] = []
        for other in MODELS:
            if other == anchor:
                continue
            for seed in SEEDS:
                anchor_rows = load_csv(
                    OUTPUT_ROOT / test_set / anchor / f"seed_{seed}" / "predictions.csv"
                )
                other_rows = load_csv(
                    OUTPUT_ROOT / test_set / other / f"seed_{seed}" / "predictions.csv"
                )
                if len(anchor_rows) != len(other_rows):
                    raise ContractError(
                        f"Prediction length mismatch: {test_set} {other} seed {seed}"
                    )
                anchor_paths = [row["relative_path"] for row in anchor_rows]
                if anchor_paths != [row["relative_path"] for row in other_rows]:
                    raise ContractError(
                        f"Prediction row order mismatch: {test_set} {other} seed {seed}"
                    )
                y_true = np.asarray(
                    [int(row["true_index"]) for row in anchor_rows], dtype=np.int64
                )
                other_true = np.asarray(
                    [int(row["true_index"]) for row in other_rows], dtype=np.int64
                )
                if not np.array_equal(y_true, other_true):
                    raise ContractError(
                        f"True labels mismatch: {test_set} {other} seed {seed}"
                    )
                pred_anchor = np.asarray(
                    [int(row["predicted_index"]) for row in anchor_rows], dtype=np.int64
                )
                pred_other = np.asarray(
                    [int(row["predicted_index"]) for row in other_rows], dtype=np.int64
                )
                result = paired_inference(
                    y_true,
                    pred_anchor,
                    pred_other,
                    class_count,
                    RNG_SEED + set_index * 1000 + len(comparisons),
                )
                result.update({"anchor": anchor, "other": other, "seed": seed})
                comparisons.append(result)
        p_values = [
            row["paired_randomization_test"]["two_sided_monte_carlo_p_unadjusted"]
            for row in comparisons
        ]
        for row, adjusted in zip(comparisons, holm_adjust(p_values)):
            test = row["paired_randomization_test"]
            test["holm_adjusted_p_family_15"] = adjusted
            test["reject_at_familywise_alpha_0_05"] = adjusted < 0.05
        final["test_sets"][test_set] = {
            "family_size": len(comparisons),
            "comparisons": comparisons,
        }
    output = OUTPUT_ROOT / "paired_macro_f1_comparisons.json"
    save_json(output, final)
    print(f"PAIRED MACRO-F1 COMPARISONS COMPLETE: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"PAIRED COMPARISON REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2)
