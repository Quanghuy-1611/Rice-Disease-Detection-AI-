"""Inference and Grad-CAM for the trained seven-class MobileNetV3 Large checkpoint."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import models, transforms

# This laptop's CPU runs Grad-CAM markedly faster with two PyTorch threads
# than with the 16-thread default. Keep an override for other hardware.
torch.set_num_threads(max(1, int(os.getenv("RICEAI_TORCH_THREADS", "2"))))


CLASSES = (
    "bacterial_leaf_blight", "brown_spot", "golden_apple_snail",
    "leaf_roller", "normal", "tungro", "weeds",
)
DEFAULT_CHECKPOINT = Path(__file__).resolve().parents[1] / "model" / "mobilenetv3large_7class_seed42.pt"
CHECKPOINT_PATH = Path(os.getenv("RICEAI_7CLASS_CHECKPOINT", str(DEFAULT_CHECKPOINT)))
TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BILINEAR, antialias=True),
    transforms.ToTensor(),
    transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
])


class SevenClassModel:
    def __init__(self) -> None:
        self.model: torch.nn.Module | None = None
        self.error: str | None = None
        try:
            if not CHECKPOINT_PATH.is_file():
                raise FileNotFoundError(f"Missing seven-class checkpoint: {CHECKPOINT_PATH}")
            checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
            if checkpoint.get("model_id") != "mobilenetv3large" or tuple(checkpoint.get("class_names", ())) != CLASSES:
                raise ValueError("Checkpoint architecture or class order differs from the seven-class contract")
            model = models.mobilenet_v3_large(weights=None)
            model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, len(CLASSES))
            model.load_state_dict(checkpoint["state_dict"], strict=True)
            self.model = model.eval()
        except Exception as exc:
            self.error = str(exc)

    def predict(self, image: Image.Image, explain: bool = True) -> tuple[str, float, np.ndarray | None]:
        if self.model is None:
            raise RuntimeError(self.error or "Seven-class model unavailable")
        tensor = TRANSFORM(image.convert("RGB")).unsqueeze(0)
        features: list[torch.Tensor] = []
        layer = self.model.features[-1]
        def capture(_layer, _input, output):
            output.retain_grad()
            features.append(output)
        forward_hook = layer.register_forward_hook(capture)
        try:
            with torch.enable_grad():
                logits = self.model(tensor)
                probabilities = torch.softmax(logits, dim=1)[0]
                index = int(probabilities.argmax())
                heatmap = None
                if explain and CLASSES[index] != "normal":
                    self.model.zero_grad(set_to_none=True)
                    logits[0, index].backward()
                    weights = features[0].grad.mean(dim=(2, 3), keepdim=True)
                    cam = torch.relu((weights * features[0]).sum(dim=1))[0].detach().numpy()
                    if cam.max() > 0:
                        cam = cam / cam.max()
                    heatmap = np.asarray(
                        Image.fromarray(np.uint8(cam * 255)).resize(image.size, Image.Resampling.BILINEAR),
                        dtype=np.float32,
                    ) / 255.0
                return CLASSES[index], float(probabilities[index]), heatmap
        finally:
            forward_hook.remove()


model = SevenClassModel()
