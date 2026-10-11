"""One-time paired Basic/Plus audit on the locked external eleven-class set.

This script reports selective accuracy and rejection. It never publishes Plus
automatically: the release decision also needs mask review and product QA.
"""

import json
import sys
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.api.seven_class_model import CLASSES, TRANSFORM

DATA = ROOT / "research" / "external_test_11class_v2_candidate"
LOCK = ROOT / "research" / "external_test_11class_v2.lock.json"
MODEL_DIR = ROOT / "backend" / "app" / "model"


class Samples(Dataset):
    def __init__(self, paths):
        self.paths = paths

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, index):
        path = self.paths[index]
        with Image.open(path) as image:
            return (TRANSFORM(image.convert("RGB")),
                    CLASSES.index(path.parent.name) if path.parent.name in CLASSES else -1,
                    path.parent.name)


def summarize(rows, select):
    known = [row for row in rows if row[0] >= 0]
    unseen = [row for row in rows if row[0] < 0]
    accepted = [row for row in known if select(row)[0]]
    by_group = {}
    for label in sorted({row[3] for row in rows}):
        group = [row for row in rows if row[3] == label]
        chosen = [row for row in group if select(row)[0]]
        by_group[label] = {"count": len(group), "accepted": len(chosen),
                           "accepted_accuracy": (sum(select(row)[1] == row[0] for row in chosen) / len(chosen))
                           if group[0][0] >= 0 and chosen else None,
                           "rejection_rate": 1 - len(chosen) / len(group)}
    return {
        "known_count": len(known), "unseen_count": len(unseen),
        "known_coverage": len(accepted) / len(known),
        "known_accepted_accuracy": sum(select(row)[1] == row[0] for row in accepted) / max(1, len(accepted)),
        "known_correct_per_all": sum(select(row)[1] == row[0] for row in accepted) / len(known),
        "unseen_rejection": sum(not select(row)[0] for row in unseen) / len(unseen),
        "by_group": by_group,
    }


def main():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    paths = sorted(path for path in DATA.glob("*/*") if path.suffix.lower() in {".jpg", ".png"})
    if len(paths) != lock["count"] or len(paths) != 1100:
        raise ValueError("Locked external set is incomplete")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(2)
    basic_checkpoint = torch.load(MODEL_DIR / "mobilenetv3large_7class_seed42.pt", map_location="cpu", weights_only=False)
    basic = models.mobilenet_v3_large(weights=None)
    basic.classifier[3] = torch.nn.Linear(basic.classifier[3].in_features, 7)
    basic.load_state_dict(basic_checkpoint["state_dict"], strict=True)
    basic.to(device).eval()
    swin_checkpoint = torch.load(MODEL_DIR / "swin_tiny_plus_7class.pt", map_location="cpu", weights_only=False)
    if tuple(swin_checkpoint.get("class_names", ())) != CLASSES:
        raise ValueError("Swin class order mismatch")
    swin = models.swin_t(weights=None)
    swin.head = torch.nn.Linear(swin.head.in_features, 7)
    swin.load_state_dict(swin_checkpoint["state_dict"], strict=True)
    swin.to(device).eval()
    rows = []
    loader = DataLoader(Samples(paths), batch_size=24, shuffle=False, num_workers=0)
    with torch.inference_mode():
        for index, (images, truths, names) in enumerate(loader, 1):
            images = images.to(device)
            basic_prob = basic(images).softmax(dim=1).cpu()
            swin_prob = swin(images).softmax(dim=1).cpu()
            for truth, a, b, name in zip(truths.tolist(), basic_prob, swin_prob, names):
                rows.append((truth, a.tolist(), b.tolist(), name))
            if index % 10 == 0:
                print(f"batch {index}/{len(loader)}", flush=True)

    def basic_decision(row):
        _, a, _, _ = row
        guess = max(range(7), key=lambda i: a[i])
        return a[guess] >= .95, guess

    def plus_decision(row):
        _, a, b, _ = row
        guess_a = max(range(7), key=lambda i: a[i])
        guess_b = max(range(7), key=lambda i: b[i])
        combined = [(x + y) / 2 for x, y in zip(a, b)]
        guess = max(range(7), key=lambda i: combined[i])
        return guess_a == guess_b and a[guess] >= .95 and b[guess] >= .95, guess

    report = {"dataset": "locked_external_11class_v2", "basic": summarize(rows, basic_decision),
              "plus": summarize(rows, plus_decision)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    (MODEL_DIR / "plus_external_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
