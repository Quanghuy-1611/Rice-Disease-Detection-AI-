"""Create a reproducible Plus release manifest only when measured gates pass.

The external audit is a post-hoc check after selecting the stricter consensus
rule. Its numbers are not a guarantee of field accuracy or a fresh blind test.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "backend" / "app" / "model"
CLASSES = ("bacterial_leaf_blight", "brown_spot", "golden_apple_snail",
           "leaf_roller", "normal", "tungro", "weeds")
UNSEEN = ("blast", "brown_planthopper", "dead_heart", "stem_borer")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    audit = json.loads((MODEL_DIR / "plus_external_audit.json").read_text(encoding="utf-8"))
    segment = json.loads((MODEL_DIR / "deeplabv3plus_plus_lesion.json").read_text(encoding="utf-8"))
    swin = json.loads((MODEL_DIR / "swin_tiny_plus_7class.json").read_text(encoding="utf-8"))
    plus, basic = audit["plus"], audit["basic"]
    failures = []

    def require(condition, description):
        if not condition:
            failures.append(description)

    require(audit["dataset"] == "locked_external_11class_v2" and
            plus["known_count"] == 700 and plus["unseen_count"] == 400,
            "The locked 1,100-image external audit is incomplete")
    require(plus["known_accepted_accuracy"] >= .98 and
            plus["known_accepted_accuracy"] >= basic["known_accepted_accuracy"] + .05,
            "Plus accepted accuracy must exceed Basic by at least 5 points")
    require(plus["unseen_rejection"] >= .90 and
            plus["unseen_rejection"] >= basic["unseen_rejection"] + .20,
            "Plus must reject substantially more unseen images")
    require(plus["known_coverage"] >= .50, "Plus must still answer at least half the known images")
    for name in CLASSES:
        group = plus["by_group"][name]
        require(group["accepted"] >= 15 and group["accepted_accuracy"] >= .85,
                f"Class {name} has too few reliable accepted predictions")
    for name in UNSEEN:
        require(plus["by_group"][name]["rejection_rate"] >= .85,
                f"Unseen class {name} has insufficient rejection")
    require(swin["best_validation_macro_f1"] >= .90, "Swin validation macro-F1 is too low")
    require(segment["best_validation_dice"] >= .75, "Lesion mask Dice is too low")
    best_segment = max(segment["history"], key=lambda row: row["validation"]["dice"])
    require(best_segment["validation"]["healthy_any_false_positive_rate"] <= .05,
            "Lesion mask marks too many healthy leaves")
    if failures:
        raise SystemExit("Plus release rejected:\n- " + "\n- ".join(failures))

    weights = {}
    for filename in ("mobilenetv3large_7class_seed42.pt", "swin_tiny_plus_7class.pt",
                     "deeplabv3plus_plus_lesion.pt"):
        weights[filename] = sha256(MODEL_DIR / filename)
    release = {
        "validated": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "consensus_rule": "both_classifiers_same_label_and_each_softmax_at_least_0.95",
        "weights_sha256": weights,
        "external_audit": {"known_coverage": plus["known_coverage"],
                           "accepted_accuracy": plus["known_accepted_accuracy"],
                           "unseen_rejection": plus["unseen_rejection"],
                           "tungro_accepted": plus["by_group"]["tungro"]["accepted"],
                           "tungro_accepted_accuracy": plus["by_group"]["tungro"]["accepted_accuracy"]},
        "mask_validation": {"dice": segment["best_validation_dice"],
                            "healthy_false_positive_rate": best_segment["validation"]["healthy_any_false_positive_rate"]},
        "limitations": [
            "External audit is post-hoc for the stricter consensus rule, not a fresh blind test.",
            "Predictions outside the trained seven groups can still be wrong.",
            "Tungro coverage remains low and needs more independently labelled images.",
            "Lesion segmentation was validated on RiceSeg-5932 leaf disease masks only.",
        ],
    }
    output = MODEL_DIR / "plus_release.json"
    output.write_text(json.dumps(release, indent=2), encoding="utf-8")
    print("Approved Plus release manifest")


if __name__ == "__main__":
    main()
