"""Train lesion masks on paired RiceSeg-5932 images and masks.

The masks cover leaf diseases only. No segmentation claim is made for pests,
snails, weeds, or unseen diseases. Held-out metrics remain validation metrics.
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.api.plus_segmentation import DeepLabV3Plus

SOURCE = ROOT / "research" / "segmentation_source"
ORIGINAL = SOURCE / "original" / "Rice Leaf Disease Images"
MASKS = SOURCE / "masks" / "mask-vesrion1"
BASIC = ROOT / "backend" / "app" / "model" / "mobilenetv3large_7class_seed42.pt"
CATEGORIES = ("Bacterialblight", "Blast", "Brownspot", "Tungro")


class LesionDataset(Dataset):
    def __init__(self, rows, train):
        self.rows = rows
        self.train = train
        self.normalize = transforms.Normalize((.485, .456, .406), (.229, .224, .225))

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        image_path, mask_path = self.rows[index]
        with Image.open(image_path) as image:
            image = image.convert("RGB").resize((256, 256), Image.Resampling.BILINEAR)
        if mask_path:
            with Image.open(mask_path) as mask:
                mask = mask.convert("L").resize((256, 256), Image.Resampling.NEAREST)
            mask = np.asarray(mask, dtype=np.float32) > 127
        else:
            mask = np.zeros((256, 256), dtype=bool)
        if self.train and random.random() < .5:
            image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            mask = np.fliplr(mask)
        return self.normalize(transforms.ToTensor()(image)), torch.from_numpy(mask.copy()).float().unsqueeze(0)


def rows_by_split():
    train, validation = [], []
    for category in CATEGORIES:
        pairs = []
        for mask in sorted((MASKS / category).glob("*.jpg")):
            image = ORIGINAL / category / mask.name
            if not image.is_file():
                raise FileNotFoundError(f"Unmatched mask: {mask}")
            pairs.append((image, mask))
        if not pairs:
            raise RuntimeError(f"No paired images for {category}")
        random.Random(42).shuffle(pairs)
        cut = round(.8 * len(pairs))
        train.extend(pairs[:cut])
        validation.extend(pairs[cut:])
    normal_train, normal_val = [], []
    manifest = ROOT / "research" / "splits" / "research_7class_train_validation.csv"
    dataset = ROOT / "research" / "dataset_11_collection_pool_v3"
    with manifest.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["label"] != "normal":
                continue
            target = normal_train if row["split"] == "train" else normal_val
            limit = 1000 if row["split"] == "train" else 200
            if len(target) < limit:
                target.append((dataset / row["relative_path"], None))
    train.extend(normal_train)
    validation.extend(normal_val)
    random.Random(43).shuffle(train)
    return train, validation


def run_epoch(model, loader, device, optimizer=None):
    model.train(optimizer is not None)
    total_loss = intersection = predicted_pixels = true_pixels = 0.0
    healthy_false = healthy_total = 0
    for index, (images, masks) in enumerate(loader, 1):
        images, masks = images.to(device, non_blocking=True), masks.to(device, non_blocking=True)
        if optimizer:
            optimizer.zero_grad(set_to_none=True)
        with torch.set_grad_enabled(optimizer is not None):
            logits = model(images)
            probabilities = logits.sigmoid()
            bce = F.binary_cross_entropy_with_logits(logits, masks, pos_weight=torch.tensor(20., device=device))
            soft_dice = (2 * (probabilities * masks).sum(dim=(1, 2, 3)) + 1) / (
                probabilities.sum(dim=(1, 2, 3)) + masks.sum(dim=(1, 2, 3)) + 1)
            loss = bce + (1 - soft_dice).mean()
            if optimizer:
                loss.backward()
                optimizer.step()
        total_loss += loss.item() * len(images)
        selected = (probabilities >= .5).float()
        intersection += (selected * masks).sum().item()
        predicted_pixels += selected.sum().item()
        true_pixels += masks.sum().item()
        healthy = masks.sum(dim=(1, 2, 3)) == 0
        healthy_false += int((selected[healthy].sum(dim=(1, 2, 3)) > 0).sum())
        healthy_total += int(healthy.sum())
        if optimizer and index % 100 == 0:
            print(f"  batch {index}/{len(loader)}", flush=True)
    dice = (2 * intersection) / max(1, predicted_pixels + true_pixels)
    union = predicted_pixels + true_pixels - intersection
    return {"loss": total_loss / len(loader.dataset), "dice": dice,
            "iou": intersection / max(1, union),
            "healthy_any_false_positive_rate": healthy_false / max(1, healthy_total)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--output", type=Path, default=ROOT / "backend" / "app" / "model" / "deeplabv3plus_plus_lesion.pt")
    args = parser.parse_args()
    torch.manual_seed(42)
    random.seed(42)
    np.random.seed(42)
    torch.set_num_threads(2)
    if not torch.cuda.is_available():
        raise RuntimeError("Training requires CUDA on this laptop")
    train, validation = rows_by_split()
    print(f"Pairs: train={len(train)}, validation={len(validation)}", flush=True)
    device = torch.device("cuda")
    model = DeepLabV3Plus()
    checkpoint = torch.load(BASIC, map_location="cpu", weights_only=False)
    encoder = {key.removeprefix("features."): value for key, value in checkpoint["state_dict"].items()
               if key.startswith("features.")}
    model.encoder.load_state_dict(encoder, strict=True)
    model.to(device)
    train_loader = DataLoader(LesionDataset(train, True), batch_size=args.batch_size,
                              shuffle=True, num_workers=args.workers, pin_memory=True,
                              drop_last=True)
    val_loader = DataLoader(LesionDataset(validation, False), batch_size=args.batch_size,
                            shuffle=False, num_workers=args.workers, pin_memory=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=.001)
    best = -1.0
    history = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for epoch_index in range(args.epochs):
        print(f"epoch {epoch_index + 1}/{args.epochs}", flush=True)
        training = run_epoch(model, train_loader, device, optimizer)
        validation_result = run_epoch(model, val_loader, device)
        history.append({"epoch": epoch_index + 1, "train": training, "validation": validation_result})
        print(f"  train Dice={training['dice']:.4f} val Dice={validation_result['dice']:.4f}", flush=True)
        if validation_result["dice"] > best:
            best = validation_result["dice"]
            torch.save({"model_id": "deeplabv3plus_mobilenetv3", "source": "RiceSeg-5932",
                        "state_dict": {k: v.cpu() for k, v in model.state_dict().items()},
                        "validation": validation_result}, args.output)
            args.output.with_suffix(".json").write_text(json.dumps({"history": history,
                "best_validation_dice": best, "paired_train": len(train),
                "paired_validation": len(validation)}, indent=2), encoding="utf-8")
    print(f"Completed: validation Dice={best:.4f}", flush=True)


if __name__ == "__main__":
    main()
