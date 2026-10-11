"""Two-classifier Plus inference with a validated lesion-mask heatmap branch."""

from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageFilter
from torchvision import models, transforms

from app.api.plus_segmentation import DeepLabV3Plus
from app.api.seven_class_model import CLASSES, TRANSFORM, model as basic_model

MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
LEAF_DISEASES = {"bacterial_leaf_blight", "brown_spot", "tungro"}
SEGMENT_TRANSFORM = transforms.Compose([
    transforms.Resize((256, 256)), transforms.ToTensor(),
    transforms.Normalize((.485, .456, .406), (.229, .224, .225)),
])


class PlusModel:
    def __init__(self):
        self.swin = None
        self.segmenter = None

    def load(self):
        if self.swin is not None:
            return
        swin_checkpoint = torch.load(MODEL_DIR / "swin_tiny_plus_7class.pt",
                                     map_location="cpu", weights_only=False)
        if swin_checkpoint.get("model_id") != "swin_tiny" or tuple(swin_checkpoint.get("class_names", ())) != CLASSES:
            raise ValueError("Plus classifier checkpoint does not match the seven-class contract")
        swin = models.swin_t(weights=None)
        swin.head = torch.nn.Linear(swin.head.in_features, len(CLASSES))
        swin.load_state_dict(swin_checkpoint["state_dict"], strict=True)
        segment_checkpoint = torch.load(MODEL_DIR / "deeplabv3plus_plus_lesion.pt",
                                        map_location="cpu", weights_only=False)
        if segment_checkpoint.get("model_id") != "deeplabv3plus_mobilenetv3":
            raise ValueError("Plus segmenter checkpoint has the wrong architecture")
        segmenter = DeepLabV3Plus()
        segmenter.load_state_dict(segment_checkpoint["state_dict"], strict=True)
        self.swin = swin.eval()
        self.segmenter = segmenter.eval()

    def predict_one(self, image: Image.Image) -> dict:
        if basic_model.model is None:
            raise RuntimeError("Basic model unavailable")
        self.load()
        image = image.convert("RGB")
        tensor = TRANSFORM(image).unsqueeze(0)
        with torch.inference_mode():
            basic_prob = basic_model.model(tensor).softmax(dim=1)[0]
            swin_prob = self.swin(tensor).softmax(dim=1)[0]
        basic_index = int(basic_prob.argmax())
        swin_index = int(swin_prob.argmax())
        consensus = basic_index == swin_index
        combined = (basic_prob + swin_prob) / 2
        index = int(combined.argmax())
        confidence = float(combined[index])
        # Each independent classifier must clear the threshold. A high average
        # can otherwise hide one model that is much less certain.
        uncertain = not consensus or float(basic_prob[index]) < .95 or float(swin_prob[index]) < .95
        heatmap = None
        if not uncertain and CLASSES[index] != "normal":
            _, _, heatmap = basic_model.predict(image, explain=True)
            if heatmap is not None and CLASSES[index] in LEAF_DISEASES:
                with torch.inference_mode():
                    mask = self.segmenter(SEGMENT_TRANSFORM(image).unsqueeze(0)).sigmoid()[0, 0]
                mask_image = Image.fromarray(np.uint8((mask.numpy() >= .5) * 255))
                mask_image = mask_image.resize(image.size, Image.Resampling.NEAREST)
                mask_image = mask_image.filter(ImageFilter.MaxFilter(9))
                heatmap = heatmap * (np.asarray(mask_image, dtype=np.float32) / 255.0)
        return {"prediction": None if uncertain else CLASSES[index],
                "confidence": confidence, "uncertain": uncertain,
                "disagreement": not consensus, "heatmap": heatmap,
                "mask_applied": not uncertain and CLASSES[index] in LEAF_DISEASES}


plus_model = PlusModel()
