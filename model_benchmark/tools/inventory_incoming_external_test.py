from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
LABELS = [
    "bacterial_leaf_blight", "blast", "brown_planthopper", "brown_spot",
    "dead_heart", "golden_apple_snail", "leaf_roller", "normal",
    "stem_borer", "tungro", "weeds",
]

# Only unambiguous, non-augmented folders are accepted. Matching is relative to
# incoming_sources and deliberately exact so newly added folders cannot silently
# enter the external-test candidate pool.
ACCEPTED_FOLDERS = {
    "Pest_V2/asiatic rice borer": "stem_borer",
    "Pest_V2/brown plant hopper": "brown_planthopper",
    "Pest_V2/rice leaf roller": "leaf_roller",
    "Pest_V2/yellow rice borer": "stem_borer",
    "RiceLeafDiseaseBD/Original images/Blast": "blast",
    "RiceLeafDiseaseBD/Original images/Brown spot": "brown_spot",
    "RiceLeafDiseaseBD/Original images/Healthy": "normal",
    "RiceLeafDiseaseBD/Original images/Rice Tungro": "tungro",
    "Stem Borer Infestation Dataset/Original Dataset/Dead Heart": "dead_heart",
    "Stem Borer Infestation Dataset/Original Dataset/Healthy": "normal",
    "ZAMBALI_RICE_DATASET_V3/BACTERIAL_BLIGHT": "bacterial_leaf_blight",
    "ZAMBALI_RICE_DATASET_V3/BROWN_SPOT": "brown_spot",
    "ZAMBALI_RICE_DATASET_V3/HEALTHY": "normal",
    "ZAMBALI_RICE_DATASET_V3/LEAF_BLAST": "blast",
}

EXCLUDED_FOLDERS = {
    "Pest_V2/paddy stem maggot": "different pest",
    "Pest_V2/rice gall midge": "different pest",
    "Pest_V2/rice leaf caterpillar": "different pest; not assumed to be leaf roller",
    "Pest_V2/rice leafhopper": "different pest",
    "Pest_V2/rice water weevil": "different pest",
    "Pest_V2/small brown plant hopper": "different species from brown planthopper label",
    "Stem Borer Infestation Dataset/Original Dataset/White Head": "symptom not present in locked taxonomy",
    "ZAMBALI_RICE_DATASET_V3/NOT_A_RICE_LEAF": "out of taxonomy",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pixel_digest(image: Image.Image) -> str:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    digest = hashlib.sha256()
    digest.update(f"{rgb.width}x{rgb.height}:RGB:".encode("ascii"))
    digest.update(rgb.tobytes())
    return digest.hexdigest()


def dct_matrix(size: int = 32, keep: int = 8) -> np.ndarray:
    x = np.arange(size, dtype=np.float64)
    k = np.arange(keep, dtype=np.float64)[:, None]
    matrix = np.cos((np.pi / size) * (x + 0.5) * k)
    matrix[0] *= np.sqrt(1.0 / size)
    matrix[1:] *= np.sqrt(2.0 / size)
    return matrix


DCT = dct_matrix()


def phash64(image: Image.Image) -> int:
    gray = ImageOps.exif_transpose(image).convert("L").resize((32, 32), Image.Resampling.LANCZOS)
    values = np.asarray(gray, dtype=np.float64)
    coeff = DCT @ values @ DCT.T
    low = coeff[:8, :8].reshape(-1)
    median = float(np.median(low[1:]))
    value = 0
    for bit in low > median:
        value = (value << 1) | int(bit)
    return value


def canonical_phash(image: Image.Image) -> int:
    base = ImageOps.exif_transpose(image).convert("RGB")
    variants = []
    current = base
    for _ in range(4):
        variants.extend((current, ImageOps.mirror(current)))
        current = current.rotate(90, expand=True)
    return min(phash64(item) for item in variants)


class BKTree:
    def __init__(self) -> None:
        self.root: tuple[int, dict[int, object]] | None = None

    def add(self, value: int) -> None:
        if self.root is None:
            self.root = (value, {})
            return
        node = self.root
        while True:
            current, children = node
            distance = (current ^ value).bit_count()
            child = children.get(distance)
            if child is None:
                children[distance] = (value, {})
                return
            node = child  # type: ignore[assignment]

    def nearest(self, value: int, limit: int) -> tuple[int, int] | None:
        if self.root is None:
            return None
        best: tuple[int, int] | None = None
        pending = [self.root]
        while pending:
            current, children = pending.pop()
            distance = (current ^ value).bit_count()
            if distance <= limit and (best is None or distance < best[0]):
                best = (distance, current)
            radius = limit if best is None else min(limit, best[0])
            pending.extend(child for edge, child in children.items() if distance - radius <= edge <= distance + radius)
        return best


def discover(incoming: Path) -> tuple[list[tuple[Path, str, str]], list[dict[str, object]]]:
    accepted: list[tuple[Path, str, str]] = []
    folder_report: list[dict[str, object]] = []
    for relative, label in ACCEPTED_FOLDERS.items():
        folder = incoming / Path(relative)
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS) if folder.is_dir() else []
        accepted.extend((path, label, relative) for path in files)
        folder_report.append({"folder": relative, "decision": "accepted", "label": label, "images": len(files)})
    for relative, reason in EXCLUDED_FOLDERS.items():
        folder = incoming / Path(relative)
        files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS) if folder.is_dir() else []
        folder_report.append({"folder": relative, "decision": "excluded", "reason": reason, "images": len(files)})
    return accepted, folder_report


def connected_representatives(records: list[dict[str, object]], threshold: int = 8) -> set[int]:
    by_label: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        if record["eligible_vs_v3"]:
            by_label[str(record["label"])].append(index)
    representatives: set[int] = set()
    for indices in by_label.values():
        adjacency: dict[int, list[int]] = defaultdict(list)
        for offset, left in enumerate(indices):
            a = int(str(records[left]["canonical_phash64"]), 16)
            for right in indices[offset + 1:]:
                b = int(str(records[right]["canonical_phash64"]), 16)
                if (a ^ b).bit_count() <= threshold:
                    adjacency[left].append(right)
                    adjacency[right].append(left)
        unseen = set(indices)
        while unseen:
            start = min(unseen)
            component = []
            queue = deque([start])
            unseen.remove(start)
            while queue:
                item = queue.popleft()
                component.append(item)
                for neighbor in adjacency[item]:
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
            # Prefer the largest image, then deterministic path order.
            chosen = min(component, key=lambda i: (-int(records[i]["area"]), str(records[i]["relative_path"])))
            representatives.add(chosen)
    return representatives


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming", type=Path, required=True)
    parser.add_argument("--v3-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--copy-root", type=Path, required=True)
    args = parser.parse_args()
    incoming, output, copy_root = args.incoming.resolve(), args.output.resolve(), args.copy_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    copy_root.mkdir(parents=True, exist_ok=True)

    with args.v3_manifest.open(encoding="utf-8-sig", newline="") as handle:
        v3 = list(csv.DictReader(handle))
    v3_sha = {row["sha256"] for row in v3}
    v3_pixel = {row["pixel_sha256"] for row in v3}
    v3_phashes = sorted({int(row["phash"], 16) for row in v3})
    tree = BKTree()
    for value in v3_phashes:
        tree.add(value)

    candidates, folder_report = discover(incoming)
    records: list[dict[str, object]] = []
    corrupt: list[dict[str, str]] = []
    for number, (path, label, source_folder) in enumerate(candidates, 1):
        relative = path.relative_to(incoming).as_posix()
        try:
            byte_sha = sha256_file(path)
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                pixels = pixel_digest(image)
                perceptual = canonical_phash(image)
            nearest = tree.nearest(perceptual, 8)
            exact = byte_sha in v3_sha
            pixel_exact = pixels in v3_pixel
            records.append({
                "relative_path": relative, "source_folder": source_folder, "label": label,
                "bytes": path.stat().st_size, "width": width, "height": height, "area": width * height,
                "sha256": byte_sha, "pixel_sha256": pixels, "canonical_phash64": f"{perceptual:016x}",
                "exact_vs_v3": exact, "pixel_exact_vs_v3": pixel_exact,
                "nearest_v3_phash_distance": "" if nearest is None else nearest[0],
                "eligible_vs_v3": not exact and not pixel_exact and nearest is None,
            })
        except Exception as exc:
            corrupt.append({"relative_path": relative, "error": f"{type(exc).__name__}: {exc}"})
        if number % 500 == 0 or number == len(candidates):
            print(f"Fingerprinted {number}/{len(candidates)}", flush=True)

    representatives = connected_representatives(records)
    copied_counts: Counter[str] = Counter()
    for index, record in enumerate(records):
        selected = index in representatives
        record["selected_external_candidate"] = selected
        record["output_relative_path"] = ""
        if not selected:
            continue
        label = str(record["label"])
        suffix = Path(str(record["relative_path"])).suffix.lower()
        target_rel = Path(label) / f"{label}_{copied_counts[label] + 1:04d}{suffix}"
        target = copy_root / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(incoming / Path(str(record["relative_path"])), target)
        copied_counts[label] += 1
        record["output_relative_path"] = target_rel.as_posix()

    columns = [
        "relative_path", "source_folder", "label", "bytes", "width", "height", "area", "sha256",
        "pixel_sha256", "canonical_phash64", "exact_vs_v3", "pixel_exact_vs_v3",
        "nearest_v3_phash_distance", "eligible_vs_v3", "selected_external_candidate", "output_relative_path",
    ]
    with (output / "incoming_inventory.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader(); writer.writerows(records)
    with (output / "folder_decisions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        columns2 = sorted({key for row in folder_report for key in row})
        writer = csv.DictWriter(handle, fieldnames=columns2)
        writer.writeheader(); writer.writerows(folder_report)

    per_label = {}
    for label in LABELS:
        rows = [row for row in records if row["label"] == label]
        per_label[label] = {
            "inventoried": len(rows),
            "exact_or_pixel_duplicate_vs_v3": sum(bool(r["exact_vs_v3"] or r["pixel_exact_vs_v3"]) for r in rows),
            "near_duplicate_phash_le8_vs_v3": sum(r["nearest_v3_phash_distance"] != "" for r in rows),
            "eligible_after_v3_screen": sum(bool(r["eligible_vs_v3"]) for r in rows),
            "selected_independent_phash8_representatives": copied_counts[label],
        }
    report = {
        "schema_version": "riceai-incoming-external-candidates/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "incoming_root": str(incoming), "v3_manifest": str(args.v3_manifest.resolve()),
        "copy_root": str(copy_root),
        "policy": {
            "source_filter": "only explicitly mapped original/non-augmented folders",
            "v3_exclusion": "SHA-256, decoded-pixel SHA-256, or canonical pHash64 distance <= 8",
            "internal_dedup": "one representative per same-label canonical-pHash connected component at distance <= 8",
            "status": "candidate set; requires visual/expert label review before locked external evaluation",
        },
        "folders": folder_report, "per_label": per_label, "corrupt_images": corrupt,
        "totals": {"inventoried": len(records), "corrupt": len(corrupt), "selected": sum(copied_counts.values())},
    }
    with (output / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report["totals"] | {"per_label_selected": dict(copied_counts)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
