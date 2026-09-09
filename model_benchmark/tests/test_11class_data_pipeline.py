from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from audit_dataset_v4 import canonical_phash, pixel_digest  # noqa: E402
from create_grouped_split_11class import allocate, cluster  # noqa: E402


class FingerprintTests(unittest.TestCase):
    def make_image(self) -> Image.Image:
        array = np.zeros((96, 128, 3), dtype=np.uint8)
        array[10:70, 15:45] = (30, 180, 70)
        array[35:85, 60:115] = (210, 90, 20)
        return Image.fromarray(array, "RGB")

    def test_canonical_phash_is_rotation_and_mirror_invariant(self) -> None:
        image = self.make_image()
        expected = canonical_phash(image)
        variants = [
            ImageOps.mirror(image),
            image.rotate(90, expand=True),
            ImageOps.mirror(image.rotate(270, expand=True)),
        ]
        self.assertTrue(all(canonical_phash(item) == expected for item in variants))

    def test_pixel_digest_tracks_decoded_pixels(self) -> None:
        image = self.make_image()
        self.assertEqual(pixel_digest(image), pixel_digest(image.copy()))
        changed = image.copy()
        changed.putpixel((0, 0), (255, 255, 255))
        self.assertNotEqual(pixel_digest(image), pixel_digest(changed))


class GroupingTests(unittest.TestCase):
    def test_cluster_uses_hamming_threshold_and_transitivity(self) -> None:
        rows = [
            {"phash": "0000000000000000"},
            {"phash": "0000000000000001"},
            {"phash": "0000000000000003"},
            {"phash": "ffffffffffffffff"},
        ]
        groups = cluster(rows, threshold=1)
        members = sorted(sorted(group) for group in groups)
        self.assertEqual(members, [[0, 1, 2], [3]])

    def test_cluster_is_complete_at_distance_eight(self) -> None:
        # One differing bit in every byte: an 8-bit-band LSH implementation
        # would miss this pair even though its true Hamming distance is 8.
        rows = [
            {"phash": "0000000000000000"},
            {"phash": "0101010101010101"},
            {"phash": "ffffffffffffffff"},
        ]
        groups = cluster(rows, threshold=8)
        members = sorted(sorted(group) for group in groups)
        self.assertEqual(members, [[0, 1], [2]])
    def test_allocate_never_splits_a_group(self) -> None:
        groups = [[0, 1, 2], [3], [4, 5], [6], [7], [8, 9]]
        import random

        assignment = allocate([group[:] for group in groups], 10, random.Random(2026))
        self.assertEqual(set(assignment), set(range(10)))
        for group in groups:
            self.assertEqual(len({assignment[index] for index in group}), 1)
        self.assertEqual(set(assignment.values()), {"train", "validation", "test"})


if __name__ == "__main__":
    unittest.main()
