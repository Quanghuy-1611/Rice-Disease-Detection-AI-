"""Agri-CAM: explainability utilities for the RiceAI backend.

This module deliberately keeps the raw Grad-CAM output alongside the proposed
Agri-CAM result.  Agri-CAM is an *estimate* made from classifier activation;
it must not be presented as a segmentation model or as calibrated severity
until ``app/data/agri_cam_calibration.json`` is populated from validation data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import json
import os
import uuid

import cv2
import numpy as np
import tensorflow as tf


EPSILON = 1e-8
DEFAULT_V3_BACKBONE = "mobilenetv3large_backbone"
# Only diseases whose symptom is meaningfully represented as affected leaf area.
SEVERITY_APPLICABLE_CLASSES = {
    "bacterial_leaf_blight",
    "bacterial_leaf_streak",
    "blast",
    "brown_spot",
    "downy_mildew",
    "leaf_smut",
    "sheath_blight",
    "tungro",
}


@dataclass(frozen=True)
class CamLayer:
    """A feature layer used by a CAM method.

    ``container`` is set for a nested MobileNetV3 backbone.  Keras does not
    allow an inner-layer output to be directly attached to the outer model, so
    the code rebuilds one connected multi-output graph safely.
    """

    name: str
    weight: float
    container: str | None = None


def decode_bgr(image_bytes: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Không đọc được nội dung ảnh.")
    return image


def prepare_input(image_bgr: np.ndarray, preprocessing: str) -> np.ndarray:
    """Prepare RGB input without silently applying the wrong MobileNet scaler."""

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_LINEAR)
    batch = np.expand_dims(resized.astype(np.float32), axis=0)

    if preprocessing == "mobilenet_v2":
        return tf.keras.applications.mobilenet_v2.preprocess_input(batch)
    if preprocessing == "raw_rgb_0_255":
        # MobileNetV3 bundle contains its own Rescaling layer.
        return batch
    raise ValueError(f"Không hỗ trợ preprocessing: {preprocessing}")


def _normalise(heatmap: np.ndarray) -> np.ndarray:
    heatmap = np.maximum(heatmap.astype(np.float32), 0.0)
    maximum = float(np.max(heatmap))
    return heatmap / maximum if maximum > EPSILON else np.zeros_like(heatmap)


def _top_level_rank4_layers(model: tf.keras.Model, use_multilayer: bool) -> list[CamLayer]:
    available_names = {layer.name for layer in model.layers}
    if use_multilayer and {"block_13_expand", "out_relu"}.issubset(available_names):
        # Legacy MobileNetV2 research baseline, retained for B4/B5 ablations.
        return [CamLayer("block_13_expand", 0.35), CamLayer("out_relu", 0.65)]

    layers: list[CamLayer] = []
    for layer in reversed(model.layers):
        try:
            if len(layer.output.shape) == 4:
                layers.append(CamLayer(layer.name, 1.0))
                break
        except (AttributeError, TypeError):
            continue
    if not layers:
        raise ValueError("Không tìm thấy feature layer 4 chiều để tạo CAM.")
    return layers


def default_cam_layers(model: tf.keras.Model, use_multilayer: bool) -> list[CamLayer]:
    """Return stable V3 layers, otherwise fall back to the final feature map."""

    try:
        backbone = model.get_layer(DEFAULT_V3_BACKBONE)
    except ValueError:
        return _top_level_rank4_layers(model, use_multilayer)

    if not use_multilayer:
        return [CamLayer("activation_19", 1.0, DEFAULT_V3_BACKBONE)]

    inner_names = {layer.name for layer in backbone.layers}
    # 14x14 retains small lesions; 7x7 contributes disease semantics.
    requested = [
        CamLayer("expanded_conv_10_project", 0.35, DEFAULT_V3_BACKBONE),
        CamLayer("activation_19", 0.65, DEFAULT_V3_BACKBONE),
    ]
    available = [item for item in requested if item.name in inner_names]
    if len(available) == 2:
        return available
    return [CamLayer(backbone.layers[-1].name, 1.0, DEFAULT_V3_BACKBONE)]


def _build_connected_grad_model(
    model: tf.keras.Model, layers: list[CamLayer]
) -> tf.keras.Model:
    """Create ``[feature maps..., predictions]`` while supporting nested V3."""

    nested_containers = {item.container for item in layers if item.container}
    if not nested_containers:
        outputs = [model.get_layer(item.name).output for item in layers] + [model.output]
        return tf.keras.Model(model.inputs, outputs, name="riceai_cam_model")

    if len(nested_containers) != 1 or None in nested_containers:
        raise ValueError("CAM layers phải cùng một backbone hoặc đều ở top-level.")

    container_name = nested_containers.pop()
    assert container_name is not None
    backbone = model.get_layer(container_name)
    inner_outputs = [backbone.get_layer(item.name).output for item in layers]
    # Ensure the classifier head receives the actual backbone output.  It is
    # appended after the requested maps then discarded from the visible output.
    multi_backbone = tf.keras.Model(
        backbone.inputs,
        inner_outputs + [backbone.output],
        name="riceai_multiscale_backbone",
    )
    outputs = multi_backbone(model.inputs[0])
    if not isinstance(outputs, (list, tuple)):
        outputs = [outputs]
    feature_outputs, backbone_output = list(outputs[:-1]), outputs[-1]

    prediction = backbone_output
    seen_backbone = False
    for layer in model.layers:
        if layer.name == container_name:
            seen_backbone = True
            continue
        if seen_backbone:
            prediction = layer(prediction)
    return tf.keras.Model(model.inputs, feature_outputs + [prediction], name="riceai_cam_model")


def _cam_from_activation(
    activation: tf.Tensor, grads: tf.Tensor, method: str
) -> tf.Tensor:
    if method == "gradcam":
        weights = tf.reduce_mean(grads, axis=(0, 1, 2))
    elif method == "gradcam++":
        gradients_2 = tf.square(grads)
        gradients_3 = gradients_2 * grads
        activation_sum = tf.reduce_sum(activation, axis=(0, 1, 2), keepdims=True)
        denominator = 2.0 * gradients_2 + activation_sum * gradients_3
        alpha = tf.where(
            tf.abs(denominator) > EPSILON,
            gradients_2 / (denominator + EPSILON),
            tf.zeros_like(denominator),
        )
        weights = tf.reduce_sum(alpha * tf.nn.relu(grads), axis=(0, 1, 2))
    else:
        raise ValueError(f"CAM method không hợp lệ: {method}")

    return tf.nn.relu(tf.reduce_sum(activation[0] * weights, axis=-1))


def compute_cam_maps(
    model: tf.keras.Model,
    model_input: np.ndarray,
    class_index: int,
    *,
    layers: list[CamLayer],
    method: str,
    image_size: tuple[int, int],
) -> tuple[list[np.ndarray], np.ndarray]:
    """Return individual normalised CAMs and their weighted multi-layer fusion."""

    grad_model = _build_connected_grad_model(model, layers)
    input_tensor = tf.convert_to_tensor(model_input)
    with tf.GradientTape(persistent=True) as tape:
        outputs = grad_model(input_tensor, training=False)
        if not isinstance(outputs, (list, tuple)):
            outputs = [outputs]
        feature_maps, predictions = list(outputs[:-1]), outputs[-1]
        score = predictions[:, class_index]

    individual: list[np.ndarray] = []
    for feature_map in feature_maps:
        gradients = tape.gradient(score, feature_map)
        if gradients is None:
            raise RuntimeError("Không tính được gradient CAM cho feature layer.")
        map_tensor = _cam_from_activation(feature_map, gradients, method)
        map_array = map_tensor.numpy()
        map_array = cv2.resize(map_array, image_size, interpolation=cv2.INTER_LINEAR)
        individual.append(_normalise(map_array))
    del tape

    weights = np.asarray([item.weight for item in layers], dtype=np.float32)
    weights = weights / max(float(weights.sum()), EPSILON)
    fusion = _normalise(sum(weight * item for weight, item in zip(weights, individual)))
    return individual, fusion


def _hsv_range(hsv: np.ndarray, lower: tuple[int, int, int], upper: tuple[int, int, int]) -> np.ndarray:
    return cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))


def create_disease_aware_leaf_mask(
    image_bgr: np.ndarray, predicted_class: str
) -> tuple[np.ndarray, dict[str, float | str]]:
    """Create a conservative green + chlorotic + necrotic leaf candidate mask.

    Brown pixels are accepted only close to green/chlorotic tissue.  This is a
    hand-crafted biological constraint, not a learned segmentation label.
    """

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    green = _hsv_range(hsv, (25, 35, 25), (95, 255, 255))
    chlorotic = _hsv_range(hsv, (15, 25, 65), (42, 220, 255))
    # Dark/yellow/brown tissue.  Constraining it near a leaf anchor prevents
    # most soil from entering the mask, while preserving disease lesions.
    necrotic = cv2.bitwise_or(
        _hsv_range(hsv, (0, 20, 20), (25, 255, 210)),
        _hsv_range(hsv, (0, 0, 20), (180, 70, 150)),
    )
    anchor = cv2.bitwise_or(green, chlorotic)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    anchor_dilated = cv2.dilate(anchor, kernel, iterations=2)
    constrained_necrosis = cv2.bitwise_and(necrotic, anchor_dilated)
    candidate = cv2.bitwise_or(anchor, constrained_necrosis)

    # For severe leaf diseases, a little larger closing connects yellow/brown
    # regions while all other classes stay conservative.
    close_size = 11 if predicted_class in SEVERITY_APPLICABLE_CLASSES else 7
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_CLOSE, close_kernel)
    candidate = cv2.morphologyEx(candidate, cv2.MORPH_OPEN, kernel)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
    retained = np.zeros_like(candidate)
    min_area = max(80, int(image_bgr.shape[0] * image_bgr.shape[1] * 0.002))
    for label in range(1, count):
        if int(stats[label, cv2.CC_STAT_AREA]) >= min_area:
            retained[labels == label] = 255

    leaf_area_ratio = float(np.count_nonzero(retained)) / float(retained.size)
    return retained.astype(np.float32) / 255.0, {
        "leaf_area_ratio": leaf_area_ratio,
        "mask_strategy": "green_chlorotic_necrotic_anchor_constrained_v1",
        "mask_status": "ok" if leaf_area_ratio >= 0.02 else "too_small",
    }


def create_simple_green_mask(image_bgr: np.ndarray) -> np.ndarray:
    """Deliberately simple HSV-green baseline (B2), not the Agri-CAM mask."""

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    green = _hsv_range(hsv, (25, 35, 25), (95, 255, 255))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    green = cv2.morphologyEx(green, cv2.MORPH_OPEN, kernel)
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, kernel)
    return green.astype(np.float32) / 255.0


def apply_leaf_constraint(heatmap: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """Do not re-normalise after masking; calibrated thresholds need this scale."""

    return np.clip(heatmap, 0.0, 1.0) * np.clip(leaf_mask, 0.0, 1.0)


def _save_image(path: str, image: np.ndarray) -> str:
    if not cv2.imwrite(path, image):
        raise OSError(f"Không thể lưu ảnh: {path}")
    return os.path.basename(path)


def _overlay(image_bgr: np.ndarray, heatmap: np.ndarray) -> np.ndarray:
    colour = cv2.applyColorMap(np.uint8(np.clip(heatmap, 0, 1) * 255), cv2.COLORMAP_JET)
    return cv2.addWeighted(image_bgr, 0.60, colour, 0.40, 0)


def save_agri_visualisations(
    image_bgr: np.ndarray,
    basic_heatmap: np.ndarray,
    multi_heatmap: np.ndarray,
    leaf_mask: np.ndarray,
    hybrid_heatmap: np.ndarray,
    output_dir: str,
) -> dict[str, str]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    prefix = str(uuid.uuid4())
    return {
        "heatmap_url": _save_image(os.path.join(output_dir, f"{prefix}_gradcam.jpg"), _overlay(image_bgr, basic_heatmap)),
        "ai_heatmap_url": _save_image(os.path.join(output_dir, f"{prefix}_cam_multi.jpg"), _overlay(image_bgr, multi_heatmap)),
        "leaf_mask_url": _save_image(os.path.join(output_dir, f"{prefix}_leaf_mask.png"), np.uint8(leaf_mask * 255)),
        "hybrid_heatmap_url": _save_image(os.path.join(output_dir, f"{prefix}_agri_cam.jpg"), _overlay(image_bgr, hybrid_heatmap)),
    }


def load_calibration(path: str | Path) -> dict[str, Any]:
    calibration_path = Path(path)
    if not calibration_path.is_file():
        return {"status": "not_calibrated", "classes": {}}
    with calibration_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if data.get("status") != "calibrated":
        return {"status": "not_calibrated", "classes": {}}
    return data


def estimate_severity(
    hybrid_heatmap: np.ndarray,
    leaf_mask: np.ndarray,
    predicted_class: str,
    calibration: dict[str, Any],
) -> dict[str, Any]:
    if predicted_class not in SEVERITY_APPLICABLE_CLASSES:
        return {
            "severity_percent": None,
            "severity_method": "not_applicable_non_leaf_area_class",
            "reliability": "not_applicable",
        }
    class_config = calibration.get("classes", {}).get(predicted_class)
    if not class_config:
        return {
            "severity_percent": None,
            "severity_method": "not_calibrated",
            "reliability": "not_calibrated",
        }

    threshold = float(class_config["threshold"])
    temperature = max(float(class_config.get("temperature", 0.10)), EPSILON)
    soft_activation = 1.0 / (1.0 + np.exp(-(hybrid_heatmap - threshold) / temperature))
    denominator = float(np.sum(leaf_mask))
    severity = 100.0 * float(np.sum(leaf_mask * soft_activation)) / max(denominator, EPSILON)
    return {
        "severity_percent": round(float(np.clip(severity, 0.0, 100.0)), 2),
        "severity_method": "soft_threshold_class_calibrated",
        "threshold": threshold,
        "temperature": temperature,
        "reliability": "review_required",  # upgraded after stability evaluation
    }


def background_attention_leakage(heatmap: np.ndarray, leaf_mask: np.ndarray) -> float:
    total = float(np.sum(heatmap))
    if total <= EPSILON:
        return 0.0
    return float(np.sum(heatmap * (1.0 - leaf_mask)) / total)


def make_stability_variants(image_bgr: np.ndarray) -> Iterable[np.ndarray]:
    """Five lightweight, deterministic perturbations for uncertainty scoring."""

    yield image_bgr
    for alpha, beta in ((0.92, -8), (1.08, 8)):
        yield cv2.convertScaleAbs(image_bgr, alpha=alpha, beta=beta)
    height, width = image_bgr.shape[:2]
    centre = (width / 2.0, height / 2.0)
    for angle in (-3.0, 3.0):
        transform = cv2.getRotationMatrix2D(centre, angle, 1.0)
        yield cv2.warpAffine(
            image_bgr,
            transform,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )


def attach_reliability(
    severity: dict[str, Any],
    samples: list[float],
    mask_status: str,
    calibration: dict[str, Any],
) -> dict[str, Any]:
    """Attach uncertainty only after the class threshold has been calibrated."""

    if severity.get("severity_percent") is None:
        return severity
    std = float(np.std(samples, ddof=0)) if samples else float("nan")
    max_std = float(calibration.get("reliability_max_std_percent", 7.0))
    severity["uncertainty_std_percent"] = round(std, 2)
    severity["stability_sample_count"] = len(samples)
    severity["reliability"] = (
        "reliable"
        if mask_status == "ok" and np.isfinite(std) and std <= max_std
        else "review_required"
    )
    return severity
