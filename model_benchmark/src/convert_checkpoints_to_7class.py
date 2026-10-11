"""Create seven-output deployment checkpoints by pruning four logits; no training."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch

from model_factory import build_model


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "runs" / "training_research_v3_stablefp32"
OUTPUT = ROOT / "runs" / "deployment_7class_pruned"
OLD_CLASSES = [
    "bacterial_leaf_blight", "blast", "brown_planthopper", "brown_spot", "dead_heart",
    "golden_apple_snail", "leaf_roller", "normal", "stem_borer", "tungro", "weeds",
]
NEW_CLASSES = [
    "bacterial_leaf_blight", "brown_spot", "golden_apple_snail",
    "leaf_roller", "normal", "tungro", "weeds",
]
KEEP = [OLD_CLASSES.index(label) for label in NEW_CLASSES]
MODELS = ["mobilenetv2", "mobilenetv3large", "resnet18", "efficientnetb0", "shufflenetv2_1_0x"]
SEEDS = [42, 123, 2026]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for model_id in MODELS:
        for seed in SEEDS:
            source = SOURCE / model_id / f"seed_{seed}" / "best_model.pt"
            if not source.is_file():
                raise SystemExit(f"Missing source checkpoint: {source}")
            checkpoint = torch.load(source, map_location="cpu", weights_only=False)
            if checkpoint.get("model_id") != model_id or checkpoint.get("class_names") != OLD_CLASSES:
                raise SystemExit(f"Unexpected checkpoint schema: {source}")
            state = checkpoint.get("state_dict")
            if not isinstance(state, dict):
                raise SystemExit(f"No state_dict: {source}")
            changed = []
            converted = {}
            for key, value in state.items():
                if isinstance(value, torch.Tensor) and value.ndim >= 1 and value.shape[0] == len(OLD_CLASSES):
                    converted[key] = value[KEEP].clone()
                    changed.append({"key": key, "old_shape": list(value.shape), "new_shape": list(converted[key].shape)})
                else:
                    converted[key] = value
            if len(changed) != 2:
                raise SystemExit(f"Expected final weight and bias only, got {changed} in {source}")
            bundle = build_model(model_id, len(NEW_CLASSES), 0.4, load_pretrained=False)
            bundle.model.load_state_dict(converted, strict=True)
            destination = OUTPUT / model_id / f"seed_{seed}" / "model_7class.pt"
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload = dict(checkpoint)
            payload["class_names"] = NEW_CLASSES
            payload["state_dict"] = converted
            payload["conversion"] = {
                "method": "output_head_row_selection_without_training",
                "source_checkpoint": str(source.resolve()),
                "source_sha256": digest(source),
                "retained_original_indices": KEEP,
                "removed_classes": [label for label in OLD_CLASSES if label not in NEW_CLASSES],
                "changed_tensors": changed,
                "warning": "For deployment/secondary analysis; not equivalent to training a seven-class model from scratch.",
            }
            torch.save(payload, destination)
            records.append({"model": model_id, "seed": seed, "path": str(destination.resolve()),
                            "sha256": digest(destination), "changed_tensors": changed})
            print(f"CONVERTED {model_id}/seed_{seed}", flush=True)
    manifest = {
        "schema_version": "riceai-pruned-checkpoints/v1",
        "training_performed": False,
        "class_names": NEW_CLASSES,
        "source_class_count": 11,
        "output_class_count": 7,
        "method": "Retain seven rows of the trained final affine layer and discard four rows.",
        "scientific_scope": "deployment or transparent secondary analysis, not a new seven-class training experiment",
        "checkpoints": records,
    }
    manifest_path = OUTPUT / "conversion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "checkpoints": len(records),
                      "classes": NEW_CLASSES, "manifest": str(manifest_path.resolve())}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
