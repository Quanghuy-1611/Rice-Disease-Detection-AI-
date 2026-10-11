"""Train the independent Swin-Tiny Plus classifier on the locked 7-class split.

The validation split is used for model selection only. No external/test images
are read. This is a product model, separate from the research comparison lock.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[2]
CLASSES = ("bacterial_leaf_blight", "brown_spot", "golden_apple_snail",
           "leaf_roller", "normal", "tungro", "weeds")
MANIFEST = ROOT / "research" / "splits" / "research_7class_train_validation.csv"
IMAGE_ROOT = ROOT / "research" / "dataset_11_collection_pool_v3"


class RiceDataset(Dataset):
    def __init__(self, rows, transform):
        self.rows = rows
        self.transform = transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        path = (IMAGE_ROOT / row["relative_path"]).resolve()
        path.relative_to(IMAGE_ROOT.resolve())
        with Image.open(path) as image:
            return self.transform(image.convert("RGB")), int(row["label_index"])


def score(truth, predicted):
    matrix = np.zeros((7, 7), dtype=np.int64)
    np.add.at(matrix, (np.asarray(truth), np.asarray(predicted)), 1)
    tp = np.diag(matrix).astype(float)
    precision = np.divide(tp, matrix.sum(axis=0), out=np.zeros(7), where=matrix.sum(axis=0) > 0)
    recall = np.divide(tp, matrix.sum(axis=1), out=np.zeros(7), where=matrix.sum(axis=1) > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(7), where=precision + recall > 0)
    return {"accuracy": float(tp.sum() / matrix.sum()), "macro_f1": float(f1.mean()),
            "per_class_f1": f1.tolist(), "confusion_matrix": matrix.tolist()}


def epoch(model, loader, device, optimizer=None):
    model.train(optimizer is not None)
    truth, predicted = [], []
    total_loss = 0.0
    for batch_index, (images, labels) in enumerate(loader, 1):
        images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
        if optimizer:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(optimizer is not None):
            logits = model(images)
            loss = nn.functional.cross_entropy(logits, labels)
            if optimizer:
                loss.backward()
                optimizer.step()
        total_loss += loss.item() * len(labels)
        truth.extend(labels.cpu().tolist())
        predicted.extend(logits.argmax(dim=1).cpu().tolist())
        if optimizer and batch_index % 300 == 0:
            print(f"  batch {batch_index}/{len(loader)}", flush=True)
    return {"loss": total_loss / len(loader.dataset), **score(truth, predicted)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--head-epochs", type=int, default=3)
    parser.add_argument("--finetune-epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--resume-from", type=Path, default=None,
                        help="Continue fine-tuning from a previously validated Swin checkpoint")
    parser.add_argument("--output", type=Path, default=ROOT / "backend" / "app" / "model" / "swin_tiny_plus_7class.pt")
    args = parser.parse_args()
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(2)
    if not torch.cuda.is_available():
        raise RuntimeError("Training requires the CUDA GPU on this laptop")
    device = torch.device("cuda")
    rows = {"train": [], "validation": []}
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["split"] in rows:
                if CLASSES[int(row["label_index"])] != row["label"]:
                    raise ValueError("Class order differs from seven-class API")
                rows[row["split"]].append(row)
    normalize = transforms.Normalize((.485, .456, .406), (.229, .224, .225))
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)), transforms.RandomHorizontalFlip(),
        transforms.RandomAffine(18, translate=(.08, .08), scale=(.9, 1.1)),
        transforms.ColorJitter(brightness=.12, contrast=.12),
        transforms.ToTensor(), normalize,
    ])
    val_transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), normalize])
    train_loader = DataLoader(RiceDataset(rows["train"], train_transform), batch_size=args.batch_size,
                              shuffle=True, num_workers=args.workers, pin_memory=True)
    val_loader = DataLoader(RiceDataset(rows["validation"], val_transform), batch_size=args.batch_size * 2,
                            shuffle=False, num_workers=args.workers, pin_memory=True)
    weights_path = ROOT / "model_benchmark" / "swin_t-704ceda3.pth"
    if not weights_path.is_file():
        raise FileNotFoundError("Download official torchvision Swin-T weights first")
    digest = hashlib.sha256(weights_path.read_bytes()).hexdigest()
    if digest != "704ceda373461b0a224fcdddd75cd2a5e9f8064512ed47adbddef7f343fd147b":
        raise ValueError("Official Swin-T weight SHA256 mismatch")
    model = models.swin_t(weights=None)
    model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True), strict=True)
    model.head = nn.Linear(model.head.in_features, 7)
    best = -1.0
    history = []
    if args.resume_from is not None:
        checkpoint = torch.load(args.resume_from, map_location="cpu", weights_only=False)
        if checkpoint.get("model_id") != "swin_tiny" or tuple(checkpoint.get("class_names", ())) != CLASSES:
            raise ValueError("Resume checkpoint does not match the seven-class Swin contract")
        model.load_state_dict(checkpoint["state_dict"], strict=True)
        best = float(checkpoint["validation"]["macro_f1"])
        history_path = args.resume_from.with_suffix(".json")
        if history_path.is_file():
            history = json.loads(history_path.read_text(encoding="utf-8")).get("history", [])
    model.to(device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for phase, count, learning_rate in (("head", args.head_epochs, 1e-3), ("finetune", args.finetune_epochs, 2e-5)):
        for parameter in model.parameters():
            parameter.requires_grad = False
        for parameter in model.head.parameters():
            parameter.requires_grad = True
        if phase == "finetune":
            for parameter in model.features[7].parameters():
                parameter.requires_grad = True
            for parameter in model.norm.parameters():
                parameter.requires_grad = True
        optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=learning_rate, weight_decay=.01)
        for i in range(count):
            print(f"{phase} {i + 1}/{count}", flush=True)
            training = epoch(model, train_loader, device, optimizer)
            validation = epoch(model, val_loader, device)
            print(f"  train={training['macro_f1']:.4f} val={validation['macro_f1']:.4f}", flush=True)
            history.append({"phase": phase, "epoch": i + 1, "train": training, "validation": validation})
            if validation["macro_f1"] > best:
                best = validation["macro_f1"]
                torch.save({"model_id": "swin_tiny", "class_names": CLASSES,
                            "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                            "validation": validation, "seed": 42}, args.output)
                (args.output.with_suffix(".json")).write_text(json.dumps({"best_validation_macro_f1": best,
                    "split": str(MANIFEST), "history": history}, indent=2), encoding="utf-8")
                print(f"  saved best={best:.4f}", flush=True)
    print(f"Completed: validation macro-F1={best:.4f}", flush=True)


if __name__ == "__main__":
    main()
