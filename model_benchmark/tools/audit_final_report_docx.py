from __future__ import annotations

import sys
import urllib.parse
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS = {"w": W, "r": R, "pr": PR, "wp": WP}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_final_report_docx.py REPORT.docx")

    path = Path(sys.argv[1]).resolve()
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        rels = ET.fromstring(archive.read("word/_rels/document.xml.rels"))

    rel_map = {node.attrib["Id"]: node.attrib for node in rels}
    hyperlink_ids = [
        node.attrib[f"{{{R}}}id"]
        for node in document.findall(".//w:hyperlink", NS)
        if f"{{{R}}}id" in node.attrib
    ]
    bad_links: list[tuple[str, str]] = []
    for rel_id in hyperlink_ids:
        relationship = rel_map.get(rel_id, {})
        target = relationship.get("Target", "")
        parsed = urllib.parse.urlparse(target)
        valid = (
            relationship.get("TargetMode") == "External"
            and relationship.get("Type", "").endswith("/hyperlink")
            and parsed.scheme == "https"
            and bool(parsed.hostname)
        )
        if not valid:
            bad_links.append((rel_id, target))

    image_alts = [
        node.attrib.get("descr", "")
        for node in document.findall(".//wp:docPr", NS)
    ]
    tables = document.findall(".//w:tbl", NS)
    table_captions = document.findall(".//w:tblCaption", NS)
    table_descriptions = document.findall(".//w:tblDescription", NS)

    print(
        f"hyperlinks={len(hyperlink_ids)} "
        f"unique={len(set(hyperlink_ids))} bad={len(bad_links)}"
    )
    print(
        f"images={len(image_alts)} "
        f"images_with_alt={sum(bool(item.strip()) for item in image_alts)}"
    )
    print(
        f"tables={len(tables)} table_captions={len(table_captions)} "
        f"table_descriptions={len(table_descriptions)}"
    )

    assert len(hyperlink_ids) == 19, "expected 19 external source links"
    assert len(set(hyperlink_ids)) == 19, "hyperlink relationship IDs are not unique"
    assert not bad_links, f"invalid external hyperlinks: {bad_links}"
    assert image_alts and all(item.strip() for item in image_alts), "missing image alt text"
    assert len(table_captions) == len(tables), "missing table captions"
    assert len(table_descriptions) == len(tables), "missing table descriptions"
    print("OOXML AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
