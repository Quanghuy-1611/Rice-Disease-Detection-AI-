"""Reliably prefetch official torchvision weights with curl resume + SHA check."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import torch
from torchvision import models

from benchmark_common import configure_utf8_console


WEIGHTS = (
    ("mobilenetv2", models.MobileNet_V2_Weights.DEFAULT),
    ("mobilenetv3large", models.MobileNet_V3_Large_Weights.DEFAULT),
    ("resnet18", models.ResNet18_Weights.DEFAULT),
    ("efficientnetb0", models.EfficientNet_B0_Weights.DEFAULT),
    ("shufflenetv2_1_0x", models.ShuffleNet_V2_X1_0_Weights.DEFAULT),
    ("densenet121", models.DenseNet121_Weights.DEFAULT),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_hash_prefix(filename: str) -> str:
    match = re.search(r"-([0-9a-f]{8,})\.pth$", filename)
    if not match:
        raise RuntimeError(f"Official weight URL has no hash prefix: {filename}")
    return match.group(1)


def is_valid(path: Path, prefix: str) -> bool:
    return path.is_file() and sha256_file(path).startswith(prefix)


def main() -> int:
    configure_utf8_console()
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise RuntimeError("curl was not found on PATH")
    cache_dir = Path(torch.hub.get_dir()) / "checkpoints"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for model_id, weights in WEIGHTS:
        url = weights.url
        filename = Path(urlparse(url).path).name
        prefix = expected_hash_prefix(filename)
        target = cache_dir / filename
        partial = cache_dir / f"{filename}.part"
        if target.exists():
            if not is_valid(target, prefix):
                raise RuntimeError(
                    f"Existing cache file has an invalid SHA256; move it aside manually: {target}"
                )
            print(f"WEIGHT CACHE VALID: {model_id} -> {target}", flush=True)
            continue

        print(f"DOWNLOADING WEIGHT: {model_id}", flush=True)
        command = [
            curl,
            "--fail",
            "--location",
            "--http1.1",
            "--retry",
            "20",
            "--retry-delay",
            "3",
            "--retry-all-errors",
            "--connect-timeout",
            "30",
            "--continue-at",
            "-",
            "--output",
            str(partial),
            url,
        ]
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                f"curl failed for {model_id} with exit code {completed.returncode}; "
                f"partial download remains at {partial} and will be resumed next run"
            )
        if not is_valid(partial, prefix):
            actual = sha256_file(partial) if partial.exists() else "missing"
            if partial.exists():
                partial.unlink()
            raise RuntimeError(
                f"Downloaded SHA256 mismatch for {model_id}: expected prefix {prefix}, got {actual}. "
                "The invalid temporary file was removed."
            )
        partial.replace(target)
        print(f"WEIGHT DOWNLOADED AND VERIFIED: {model_id} -> {target}", flush=True)

    print("ALL OFFICIAL WEIGHTS ARE CACHED AND SHA-VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
