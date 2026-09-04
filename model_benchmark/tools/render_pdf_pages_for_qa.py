from __future__ import annotations

import argparse
from pathlib import Path

import pypdfium2 as pdfium


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--scale", type=float, default=2.0)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(args.pdf))
    for index in range(len(pdf)):
        page = pdf[index]
        image = page.render(scale=args.scale).to_pil()
        image.save(args.output_dir / f"page_{index + 1:03d}.png")
    print(f"PAGES_RENDERED={len(pdf)}")


if __name__ == "__main__":
    main()
