"""Official torchvision backbone factory for the six-model comparison."""

from __future__ import annotations

from dataclasses import dataclass
import sys
import time
from typing import Any, Callable

import torch
from torch import nn
from torchvision import models


@dataclass(frozen=True)
class ModelBundle:
    model: nn.Module
    weights_id: str
    classifier_parameter_names: tuple[str, ...]


def _replace_classifier(model_id: str, model: nn.Module, class_count: int, dropout: float) -> tuple[str, ...]:
    if model_id == "resnet18":
        in_features = model.fc.in_features
        model.fc = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_features, class_count))
        return ("fc",)
    if model_id == "shufflenetv2_1_0x":
        in_features = model.fc.in_features
        model.fc = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_features, class_count))
        return ("fc",)
    if model_id == "densenet121":
        in_features = model.classifier.in_features
        model.classifier = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_features, class_count))
        return ("classifier",)
    if model_id in {"mobilenetv2", "mobilenetv3large", "efficientnetb0"}:
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, class_count)
        # The official classifiers already contain dropout.
        for layer in model.classifier.modules():
            if isinstance(layer, nn.Dropout):
                layer.p = dropout
        return ("classifier",)
    raise ValueError(f"Unsupported model_id: {model_id}")


def build_model(
    model_id: str,
    class_count: int,
    dropout: float,
    load_pretrained: bool = True,
) -> ModelBundle:
    """Load official ImageNet-1K weights; never silently train from scratch."""
    factories: dict[str, tuple[Callable[..., nn.Module], Any]] = {
        "mobilenetv2": (models.mobilenet_v2, models.MobileNet_V2_Weights.DEFAULT),
        "mobilenetv3large": (models.mobilenet_v3_large, models.MobileNet_V3_Large_Weights.DEFAULT),
        "resnet18": (models.resnet18, models.ResNet18_Weights.DEFAULT),
        "efficientnetb0": (models.efficientnet_b0, models.EfficientNet_B0_Weights.DEFAULT),
        "shufflenetv2_1_0x": (models.shufflenet_v2_x1_0, models.ShuffleNet_V2_X1_0_Weights.DEFAULT),
        "densenet121": (models.densenet121, models.DenseNet121_Weights.DEFAULT),
    }
    if model_id not in factories:
        raise ValueError(f"Unknown model_id {model_id!r}; allowed: {sorted(factories)}")
    factory, weights = factories[model_id]
    selected_weights = weights if load_pretrained else None
    attempts = 5 if load_pretrained else 1
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            model = factory(weights=selected_weights)
            break
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                raise RuntimeError(
                    f"Cannot load official ImageNet weights for {model_id} after {attempts} attempts. "
                    "The benchmark refuses to fall back to random weights."
                ) from exc
            delay = min(30, 2 ** attempt)
            print(
                f"Weight download/load failed for {model_id} (attempt {attempt}/{attempts}): "
                f"{type(exc).__name__}. Retrying in {delay}s...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)
    else:  # pragma: no cover - defensive; the loop either breaks or raises.
        raise RuntimeError(f"Cannot construct {model_id}") from last_error
    classifier_names = _replace_classifier(model_id, model, class_count, dropout)
    return ModelBundle(
        model=model,
        weights_id=f"{weights.__class__.__name__}.{weights.name}",
        classifier_parameter_names=classifier_names,
    )


def configure_stage(model: nn.Module, classifier_names: tuple[str, ...], stage: str) -> None:
    """Apply the same transfer-learning rule to every architecture."""
    if stage not in {"head", "finetune"}:
        raise ValueError(f"Invalid stage: {stage}")
    for parameter in model.parameters():
        parameter.requires_grad = stage == "finetune"

    if stage == "head":
        for name, parameter in model.named_parameters():
            parameter.requires_grad = name.split(".", 1)[0] in classifier_names

    # Small/imbalanced agricultural datasets can destabilize pretrained BN stats.
    for module in model.modules():
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            module.eval()
            for parameter in module.parameters():
                parameter.requires_grad = False


def keep_batchnorm_frozen(model: nn.Module) -> None:
    """Call after model.train(), which otherwise re-enables BN training mode."""
    for module in model.modules():
        if isinstance(module, nn.modules.batchnorm._BatchNorm):
            module.eval()


def parameter_summary(model: nn.Module) -> dict[str, int]:
    return {
        "total_parameters": sum(parameter.numel() for parameter in model.parameters()),
        "trainable_parameters": sum(
            parameter.numel() for parameter in model.parameters() if parameter.requires_grad
        ),
    }
