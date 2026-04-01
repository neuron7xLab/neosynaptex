"""Validate SVG files for XML safety and theme-friendly rendering."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


TRANSPARENT_VALUES = {"none", "transparent", "rgba(0,0,0,0)", "rgba(0, 0, 0, 0)"}


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _is_full_rect(elem: ET.Element, view_box: tuple[float, float, float, float]) -> bool:
    width = elem.attrib.get("width", "").strip()
    height = elem.attrib.get("height", "").strip()
    vb_w = view_box[2]
    vb_h = view_box[3]
    if width in {"100%", str(int(vb_w)), str(vb_w)} and height in {"100%", str(int(vb_h)), str(vb_h)}:
        return True
    return False


def validate_svg(path: Path) -> int:
    if not path.exists():
        print(f"ERROR:{path}:missing_file")
        return 1
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except ET.ParseError:
        print(f"ERROR:{path}:xml_parse_failed")
        return 1

    if _local_name(root.tag) != "svg":
        print(f"ERROR:{path}:root_not_svg")
        return 1

    view_box_raw = root.attrib.get("viewBox")
    if not view_box_raw:
        print(f"ERROR:{path}:missing_viewBox")
        return 1

    parts = view_box_raw.replace(",", " ").split()
    if len(parts) != 4:
        print(f"ERROR:{path}:invalid_viewBox")
        return 1
    try:
        view_box = tuple(float(part) for part in parts)
    except ValueError:
        print(f"ERROR:{path}:invalid_viewBox_numbers")
        return 1

    for elem in root.iter():
        if _local_name(elem.tag) != "rect":
            continue
        fill = elem.attrib.get("fill", "none").strip().lower()
        if _is_full_rect(elem, view_box) and fill not in TRANSPARENT_VALUES:
            print(f"ERROR:{path}:full_rect_forced_background")
            return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SVG files.")
    parser.add_argument("paths", nargs="+", help="SVG path(s) to validate")
    args = parser.parse_args()

    for raw in args.paths:
        code = validate_svg(Path(raw))
        if code != 0:
            return code
    print("SVG_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
