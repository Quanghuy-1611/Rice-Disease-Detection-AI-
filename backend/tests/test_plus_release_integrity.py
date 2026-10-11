"""A retrained checkpoint disables Plus until it has a new validated release."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.api import plans


def check():
    with TemporaryDirectory() as directory:
        model_dir = Path(directory)
        hashes = {}
        for name in plans.RELEASE_WEIGHTS:
            contents = name.encode("utf-8")
            (model_dir / name).write_bytes(contents)
            hashes[name] = hashlib.sha256(contents).hexdigest()
        (model_dir / "plus_release.json").write_text(
            json.dumps({"validated": True, "weights_sha256": hashes}), encoding="utf-8")
        with patch.object(plans, "MODEL_DIR", model_dir), \
                patch.object(plans, "_approved_runtime_fingerprints", None):
            assert plans.plus_model_ready()
            checkpoint = model_dir / plans.RELEASE_WEIGHTS[1]
            checkpoint.write_bytes(b"retrained model")
            assert not plans.plus_model_ready()
            hashes[plans.RELEASE_WEIGHTS[1]] = hashlib.sha256(b"retrained model").hexdigest()
            (model_dir / "plus_release.json").write_text(
                json.dumps({"validated": True, "weights_sha256": hashes}), encoding="utf-8")
            assert not plans.plus_model_ready()
            # A restart loads the new checkpoints into memory.
            with patch.object(plans, "_approved_runtime_fingerprints", None):
                assert plans.plus_model_ready()
            (model_dir / "plus_release.json").write_text(
                json.dumps({"validated": False, "weights_sha256": hashes}), encoding="utf-8")
            assert not plans.plus_model_ready()


if __name__ == "__main__":
    check()
    print("Plus release integrity checks passed")
