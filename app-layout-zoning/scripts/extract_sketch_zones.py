#!/usr/bin/env python3
"""Extract meaningful multi-level zones from a Sketch file."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_CONTAINER_CLASSES = {"group", "symbolInstance", "artboard", "symbolMaster"}
GENERIC_NAME_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        r"^矩形$",
        r"^bg$",
        r"^蒙版$",
        r"^位图$",
        r"^编组(?: \d+)?$",
        r"^层叠 \d+$",
        r"^Home Indicators$",
        r"^电池电量条$",
        r"^导航$",
        r"^ai$",
        r"^ic_",
        r"^iPhone X/",
    ]
]

DEFAULT_COLORS_BY_LEVEL = {
    1: "#FF8A00",
    2: "#00B8D9",
    3: "#7B61FF",
}


@dataclass
class NodeZone:
    sketch_id: str
    name: str
    level: int
    parent_sketch_id: str | None
    x: int
    y: int
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract up to N levels of meaningful zone groups from a Sketch file."
    )
    parser.add_argument("sketch", type=Path, help="Path to the Sketch file")
    parser.add_argument(
        "--page-name",
        help="Sketch page name to use. Defaults to the first non-component page.",
    )
    parser.add_argument(
        "--root-name",
        help="Target root group or artboard name. Defaults to the largest top-level group.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum extraction depth below the selected root (default: 3)",
    )
    parser.add_argument(
        "--min-area-ratio",
        type=float,
        default=0.003,
        help="Skip tiny containers below this fraction of the root area (default: 0.003)",
    )
    parser.add_argument(
        "--min-width-ratio",
        type=float,
        default=0.18,
        help="Skip containers narrower than this fraction of the root width (default: 0.18)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sketch-zones.json"),
        help="Output JSON path (default: ./sketch-zones.json)",
    )
    return parser.parse_args()


def load_sketch_json(sketch_path: Path, member: str) -> dict[str, Any]:
    with zipfile.ZipFile(sketch_path) as archive:
        return json.loads(archive.read(member))


def list_page_members(sketch_path: Path) -> list[str]:
    with zipfile.ZipFile(sketch_path) as archive:
        return [name for name in archive.namelist() if name.startswith("pages/") and name.endswith(".json")]


def get_frame(layer: dict[str, Any]) -> tuple[float, float, float, float]:
    frame = layer.get("frame", {})
    return (
        float(frame.get("x", 0)),
        float(frame.get("y", 0)),
        float(frame.get("width", 0)),
        float(frame.get("height", 0)),
    )


def choose_page(sketch_path: Path, page_name: str | None) -> tuple[str, dict[str, Any]]:
    page_members = list_page_members(sketch_path)
    pages: list[tuple[str, dict[str, Any]]] = []
    for member in page_members:
        page = load_sketch_json(sketch_path, member)
        pages.append((member, page))

    if page_name:
        for member, page in pages:
            if page.get("name") == page_name:
                return member, page
        raise ValueError(f"Sketch page not found: {page_name}")

    content_pages = [item for item in pages if item[1].get("name") not in {"控件", "Symbols"}]
    if content_pages:
        return content_pages[0]
    return pages[0]


def choose_root(page: dict[str, Any], root_name: str | None) -> dict[str, Any]:
    layers = page.get("layers", [])
    if not layers:
        raise ValueError("Selected page has no layers")

    if root_name:
        for layer in layers:
            if layer.get("name") == root_name:
                return layer
        raise ValueError(f"Root layer not found: {root_name}")

    candidates = [layer for layer in layers if layer.get("_class") in VALID_CONTAINER_CLASSES]
    if not candidates:
        raise ValueError("No container-like top-level layers found on the selected page")
    return max(candidates, key=lambda layer: get_frame(layer)[2] * get_frame(layer)[3])


def is_generic_name(name: str) -> bool:
    stripped = name.strip()
    return any(pattern.search(stripped) for pattern in GENERIC_NAME_PATTERNS)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip().lower()).strip("-")
    return slug or "zone"


def should_keep(
    layer: dict[str, Any],
    level: int,
    width: int,
    height: int,
    root_width: int,
    root_area: int,
    min_area_ratio: float,
    min_width_ratio: float,
) -> bool:
    if layer.get("_class") not in VALID_CONTAINER_CLASSES:
        return False
    if width <= 0 or height <= 0:
        return False

    name = str(layer.get("name") or "").strip()
    if not name or is_generic_name(name):
        return False

    if level == 1:
        return True

    if width / root_width < min_width_ratio:
        return False
    if (width * height) / root_area < min_area_ratio:
        return False
    return True


def collect_zones(
    layer: dict[str, Any],
    *,
    max_depth: int,
    root_origin: tuple[int, int],
    root_width: int,
    root_area: int,
    min_area_ratio: float,
    min_width_ratio: float,
    level: int = 0,
    parent_kept_id: str | None = None,
) -> list[NodeZone]:
    zones: list[NodeZone] = []
    if level >= max_depth:
        return zones

    root_x, root_y = root_origin
    for child in layer.get("layers", []):
        child_x, child_y, child_w, child_h = get_frame(child)
        abs_x = int(round(root_x + child_x))
        abs_y = int(round(root_y + child_y))
        width = int(round(child_w))
        height = int(round(child_h))
        next_level = level + 1
        keep = should_keep(
            child,
            next_level,
            width,
            height,
            root_width,
            root_area,
            min_area_ratio,
            min_width_ratio,
        )

        current_parent = parent_kept_id
        if keep:
            zone = NodeZone(
                sketch_id=str(child.get("do_objectID")),
                name=str(child.get("name")),
                level=next_level,
                parent_sketch_id=parent_kept_id,
                x=abs_x,
                y=abs_y,
                width=width,
                height=height,
            )
            zones.append(zone)
            current_parent = zone.sketch_id

        zones.extend(
            collect_zones(
                child,
                max_depth=max_depth,
                root_origin=(abs_x, abs_y),
                root_width=root_width,
                root_area=root_area,
                min_area_ratio=min_area_ratio,
                min_width_ratio=min_width_ratio,
                level=next_level,
                parent_kept_id=current_parent,
            )
        )
    return zones


def build_output(
    sketch_path: Path,
    page_name: str,
    root_layer: dict[str, Any],
    zones: list[NodeZone],
) -> dict[str, Any]:
    _, _, root_w, root_h = get_frame(root_layer)
    zone_payload: list[dict[str, Any]] = []
    for index, zone in enumerate(sorted(zones, key=lambda item: (item.y, item.level, item.x))):
        zone_payload.append(
            {
                "id": f"level{zone.level}_{index + 1}",
                "label": zone.name,
                "x": zone.x,
                "y": zone.y,
                "width": zone.width,
                "height": zone.height,
                "color": DEFAULT_COLORS_BY_LEVEL.get(zone.level, "#5B8CFF"),
                "level": zone.level,
                "sketch_id": zone.sketch_id,
                "parent_sketch_id": zone.parent_sketch_id,
            }
        )

    return {
        "image": "",
        "source": {
            "type": "sketch",
            "path": str(sketch_path),
            "page_name": page_name,
            "root_name": root_layer.get("name"),
            "root_sketch_id": root_layer.get("do_objectID"),
            "root_width": int(round(root_w)),
            "root_height": int(round(root_h)),
        },
        "zones": zone_payload,
    }


def main() -> int:
    args = parse_args()
    try:
        _, page = choose_page(args.sketch, args.page_name)
        page_name = str(page.get("name") or "")
        root_layer = choose_root(page, args.root_name)
        root_x, root_y, root_w, root_h = get_frame(root_layer)
        zones = collect_zones(
            root_layer,
            max_depth=args.max_depth,
            root_origin=(0, 0),
            root_width=int(round(root_w)),
            root_area=int(round(root_w * root_h)),
            min_area_ratio=args.min_area_ratio,
            min_width_ratio=args.min_width_ratio,
        )
        payload = build_output(args.sketch.resolve(), page_name, root_layer, zones)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (ValueError, zipfile.BadZipFile, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Extracted zones: {args.output}")
    print(f"Selected page: {payload['source']['page_name']}")
    print(f"Selected root: {payload['source']['root_name']}")
    print(f"Zone count: {len(payload['zones'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
