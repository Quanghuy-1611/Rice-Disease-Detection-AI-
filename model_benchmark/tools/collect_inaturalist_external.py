from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


API = "https://api.inaturalist.org/v1/observations"
LICENSES = "cc0,cc-by,cc-by-sa,cc-by-nc"


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "RiceAI-research-dataset-audit/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "RiceAI-research-dataset-audit/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as handle:
        while block := response.read(1024 * 1024):
            handle.write(block)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--taxon-id", type=int, required=True)
    parser.add_argument("--taxon-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=180)
    parser.add_argument("--max-per-observer", type=int, default=3)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing existing output directory: {args.output}")
    image_root = args.output / "images"
    image_root.mkdir(parents=True)

    observations = []
    for page in range(1, 11):
        query = urllib.parse.urlencode({
            "taxon_id": args.taxon_id,
            "quality_grade": "research",
            "photos": "true",
            "photo_license": LICENSES,
            "per_page": 200,
            "page": page,
            "order_by": "observed_on",
            "order": "desc",
        })
        payload = get_json(f"{API}?{query}")
        observations.extend(payload.get("results", []))
        if len(observations) >= int(payload.get("total_results", 0)):
            break
        time.sleep(0.3)

    observer_counts: Counter[str] = Counter()
    records = []
    errors = []
    for observation in observations:
        if len(records) >= args.limit:
            break
        photos = observation.get("photos") or []
        if not photos:
            continue
        user = observation.get("user") or {}
        observer = str(user.get("login") or user.get("id") or "unknown")
        if observer_counts[observer] >= args.max_per_observer:
            continue
        photo = photos[0]
        license_code = str(photo.get("license_code") or "").lower()
        if license_code not in {"cc0", "cc-by", "cc-by-sa", "cc-by-nc"}:
            continue
        original_url = str(photo.get("url") or "").replace("/square.", "/large.")
        suffix = Path(urllib.parse.urlparse(original_url).path).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            suffix = ".jpg"
        target = image_root / f"inat_{observation['id']}_{photo['id']}{suffix}"
        try:
            download(original_url, target)
        except Exception as exc:
            errors.append({"observation_id": observation.get("id"), "url": original_url, "error": str(exc)})
            continue
        observer_counts[observer] += 1
        records.append({
            "relative_path": target.relative_to(args.output).as_posix(),
            "taxon_id": args.taxon_id,
            "taxon_name": args.taxon_name,
            "observation_id": observation.get("id"),
            "observation_url": f"https://www.inaturalist.org/observations/{observation.get('id')}",
            "observed_on": observation.get("observed_on") or "",
            "place_guess": observation.get("place_guess") or "",
            "observer_login": observer,
            "observer_name": user.get("name") or "",
            "photo_id": photo.get("id"),
            "photo_url": original_url,
            "photo_license": license_code,
            "attribution": photo.get("attribution") or "",
        })
        print(f"Downloaded {len(records)}/{args.limit}", flush=True)
        time.sleep(0.15)

    with (args.output / "source_manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "taxon_id": args.taxon_id,
        "taxon_name": args.taxon_name,
        "api_query_policy": "research grade; has photos; photo license in CC0/CC-BY/CC-BY-SA/CC-BY-NC",
        "one_photo_per_observation": True,
        "max_photos_per_observer": args.max_per_observer,
        "downloaded": len(records),
        "unique_observers": len(observer_counts),
        "errors": errors,
        "status": "raw incoming source; must pass label review and v3 duplicate audit",
    }
    (args.output / "source_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

