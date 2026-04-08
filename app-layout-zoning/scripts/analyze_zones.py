#!/usr/bin/env python3
"""Annotate app screenshots with zone overlays and calculate area statistics."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont


DEFAULT_COLORS = [
    "#FF8A00",
    "#00B8D9",
    "#7B61FF",
    "#00A86B",
    "#FF5C8A",
    "#E2B100",
    "#5B8CFF",
    "#FF6B3D",
    "#14B8A6",
    "#8B5CF6",
]

FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


@dataclass(frozen=True)
class Zone:
    id: str
    label: str
    x: int
    y: int
    width: int
    height: int
    color: str
    metadata: dict[str, Any]

    @property
    def x2(self) -> int:
        return self.x + self.width

    @property
    def y2(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height


class ZoneValidationError(ValueError):
    """Raised when a zone definition is invalid."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Annotate an app screenshot with rectangle zones and export area statistics."
        )
    )
    parser.add_argument("image", type=Path, help="Path to the source screenshot image")
    parser.add_argument("zones", type=Path, help="Path to the zones JSON definition")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("out"),
        help="Directory for annotated image and stats files (default: ./out)",
    )
    parser.add_argument(
        "--annotated-name",
        default="annotated.png",
        help="Output filename for the annotated image (default: annotated.png)",
    )
    parser.add_argument(
        "--json-name",
        default="stats.json",
        help="Output filename for JSON stats (default: stats.json)",
    )
    parser.add_argument(
        "--csv-name",
        default="stats.csv",
        help="Output filename for CSV stats (default: stats.csv)",
    )
    parser.add_argument(
        "--fail-on-overlap",
        action="store_true",
        help="Exit with a non-zero code when any zones overlap",
    )
    parser.add_argument(
        "--fail-on-bounds",
        action="store_true",
        help="Exit with a non-zero code when any zone is out of image bounds",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=24,
        help="Font size used for zone labels (default: 24)",
    )
    return parser.parse_args()


def load_zone_specs(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ZoneValidationError(f"Zones file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ZoneValidationError(f"Zones file is not valid JSON: {exc}") from exc


def normalize_zone(raw: dict[str, Any], index: int) -> Zone:
    required = ["id", "label", "x", "y", "width", "height"]
    missing = [field for field in required if field not in raw]
    if missing:
        raise ZoneValidationError(
            f"Zone #{index + 1} is missing required fields: {', '.join(missing)}"
        )

    try:
        x = int(raw["x"])
        y = int(raw["y"])
        width = int(raw["width"])
        height = int(raw["height"])
    except (TypeError, ValueError) as exc:
        raise ZoneValidationError(
            f"Zone #{index + 1} must use integer x/y/width/height values"
        ) from exc

    if width <= 0 or height <= 0:
        raise ZoneValidationError(
            f"Zone #{index + 1} must have positive width and height"
        )

    zone_id = str(raw["id"]).strip()
    label = str(raw["label"]).strip()
    if not zone_id or not label:
        raise ZoneValidationError(
            f"Zone #{index + 1} must have non-empty id and label values"
        )

    color = str(raw.get("color") or DEFAULT_COLORS[index % len(DEFAULT_COLORS)])
    try:
        ImageColor.getrgb(color)
    except ValueError as exc:
        raise ZoneValidationError(
            f"Zone #{index + 1} uses an invalid color value: {color}"
        ) from exc

    return Zone(
        id=zone_id,
        label=label,
        x=x,
        y=y,
        width=width,
        height=height,
        color=color,
        metadata={
            key: value
            for key, value in raw.items()
            if key not in {"id", "label", "x", "y", "width", "height", "color"}
        },
    )


def load_zones(specs: dict[str, Any]) -> list[Zone]:
    raw_zones = specs.get("zones")
    if not isinstance(raw_zones, list) or not raw_zones:
        raise ZoneValidationError("Zones JSON must contain a non-empty 'zones' array")

    zones = [normalize_zone(raw, index) for index, raw in enumerate(raw_zones)]
    ids = [zone.id for zone in zones]
    if len(ids) != len(set(ids)):
        raise ZoneValidationError("Zone ids must be unique")
    return zones


def find_out_of_bounds(zones: list[Zone], image_size: tuple[int, int]) -> list[dict[str, Any]]:
    width, height = image_size
    issues: list[dict[str, Any]] = []
    for zone in zones:
        if zone.x < 0 or zone.y < 0 or zone.x2 > width or zone.y2 > height:
            issues.append(
                {
                    "zone_id": zone.id,
                    "label": zone.label,
                    "bounds": {
                        "x": zone.x,
                        "y": zone.y,
                        "x2": zone.x2,
                        "y2": zone.y2,
                    },
                }
            )
    return issues


def intersect(a: Zone, b: Zone) -> dict[str, int] | None:
    left = max(a.x, b.x)
    top = max(a.y, b.y)
    right = min(a.x2, b.x2)
    bottom = min(a.y2, b.y2)
    if left < right and top < bottom:
        return {
            "x": left,
            "y": top,
            "width": right - left,
            "height": bottom - top,
            "area": (right - left) * (bottom - top),
        }
    return None


def find_overlaps(zones: list[Zone]) -> list[dict[str, Any]]:
    overlaps: list[dict[str, Any]] = []
    for index, left_zone in enumerate(zones):
        for right_zone in zones[index + 1 :]:
            overlap = intersect(left_zone, right_zone)
            if overlap:
                overlaps.append(
                    {
                        "zone_ids": [left_zone.id, right_zone.id],
                        "labels": [left_zone.label, right_zone.label],
                        "intersection": overlap,
                    }
                )
    return overlaps


def compute_union_area(zones: list[Zone]) -> int:
    if not zones:
        return 0

    xs = sorted({point for zone in zones for point in (zone.x, zone.x2)})
    ys = sorted({point for zone in zones for point in (zone.y, zone.y2)})
    union_area = 0

    for x_index in range(len(xs) - 1):
        left = xs[x_index]
        right = xs[x_index + 1]
        if left == right:
            continue
        for y_index in range(len(ys) - 1):
            top = ys[y_index]
            bottom = ys[y_index + 1]
            if top == bottom:
                continue
            covered = any(
                zone.x <= left and zone.x2 >= right and zone.y <= top and zone.y2 >= bottom
                for zone in zones
            )
            if covered:
                union_area += (right - left) * (bottom - top)
    return union_area


def load_font(font_size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), font_size)
            except OSError:
                continue
    return ImageFont.load_default()


def hex_to_rgba(color: str, alpha: int) -> tuple[int, int, int, int]:
    red, green, blue = ImageColor.getrgb(color)
    return red, green, blue, alpha


def draw_annotations(
    image: Image.Image,
    zones: list[Zone],
    font_size: int,
) -> Image.Image:
    annotated = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(font_size)
    padding = max(6, font_size // 4)
    outline_width = max(2, font_size // 8)

    for zone in zones:
        draw.rectangle(
            [(zone.x, zone.y), (zone.x2, zone.y2)],
            fill=hex_to_rgba(zone.color, 48),
            outline=hex_to_rgba(zone.color, 255),
            width=outline_width,
        )

        label_text = f"{zone.label} ({zone.id})"
        bbox = draw.textbbox((0, 0), label_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        label_left = zone.x
        label_top = zone.y
        label_right = min(image.width, label_left + text_width + padding * 2)
        label_bottom = min(image.height, label_top + text_height + padding * 2)

        if label_bottom - label_top < text_height + padding * 2:
            label_top = max(0, zone.y - (text_height + padding * 2))
            label_bottom = label_top + text_height + padding * 2

        draw.rectangle(
            [(label_left, label_top), (label_right, label_bottom)],
            fill=hex_to_rgba(zone.color, 220),
        )
        draw.text(
            (label_left + padding, label_top + padding),
            label_text,
            fill=(255, 255, 255, 255),
            font=font,
        )

    return Image.alpha_composite(annotated, overlay).convert("RGB")


def build_stats(
    image_path: Path,
    image_size: tuple[int, int],
    zones: list[Zone],
    overlaps: list[dict[str, Any]],
    out_of_bounds: list[dict[str, Any]],
) -> dict[str, Any]:
    image_width, image_height = image_size
    image_area = image_width * image_height
    coverage_area = compute_union_area(zones)

    zones_by_id = {zone.id: zone for zone in zones}
    zones_payload = []
    for zone in zones:
        zone_area = zone.area
        parent_id = zone.metadata.get("parent_id") or zone.metadata.get("parent_zone_id")
        if not parent_id and zone.metadata.get("parent_sketch_id"):
            for candidate in zones:
                if candidate.metadata.get("sketch_id") == zone.metadata.get("parent_sketch_id"):
                    parent_id = candidate.id
                    break

        parent_zone = zones_by_id.get(str(parent_id)) if parent_id else None
        parent_coverage_pct = None
        if parent_zone and parent_zone.area > 0:
            parent_coverage_pct = round(zone_area / parent_zone.area * 100, 4)

        zone_record = {
            "id": zone.id,
            "label": zone.label,
            "x": zone.x,
            "y": zone.y,
            "width": zone.width,
            "height": zone.height,
            "area": zone_area,
            "coverage_pct": round(zone_area / image_area * 100, 4),
            "color": zone.color,
        }
        zone_record.update(zone.metadata)
        if parent_id:
            zone_record["parent_id"] = parent_id
        if parent_coverage_pct is not None:
            zone_record["parent_coverage_pct"] = parent_coverage_pct

        zones_payload.append(zone_record)

    level_summary: dict[str, dict[str, Any]] = {}
    levels = sorted(
        {
            int(zone.metadata["level"])
            for zone in zones
            if isinstance(zone.metadata.get("level"), int)
            or (
                isinstance(zone.metadata.get("level"), str)
                and str(zone.metadata["level"]).isdigit()
            )
        }
    )
    for level in levels:
        level_zones = [
            zone
            for zone in zones
            if int(zone.metadata.get("level")) == level
        ]
        union_area = compute_union_area(level_zones)
        level_summary[str(level)] = {
            "zone_count": len(level_zones),
            "coverage_area": union_area,
            "coverage_pct": round(union_area / image_area * 100, 4),
            "sum_of_zone_areas": sum(zone.area for zone in level_zones),
            "sum_of_zone_areas_pct": round(
                sum(zone.area for zone in level_zones) / image_area * 100, 4
            ),
        }

    return {
        "image": {
            "path": str(image_path),
            "width": image_width,
            "height": image_height,
            "area": image_area,
        },
        "zones": zones_payload,
        "summary": {
            "zone_count": len(zones),
            "coverage_area": coverage_area,
            "coverage_pct": round(coverage_area / image_area * 100, 4),
            "uncovered_area": image_area - coverage_area,
            "uncovered_pct": round((image_area - coverage_area) / image_area * 100, 4),
            "sum_of_zone_areas": sum(zone.area for zone in zones),
            "sum_of_zone_areas_pct": round(
                sum(zone.area for zone in zones) / image_area * 100, 4
            ),
        },
        "level_summary": level_summary,
        "validation": {
            "out_of_bounds": out_of_bounds,
            "has_out_of_bounds": bool(out_of_bounds),
            "overlaps": overlaps,
            "has_overlaps": bool(overlaps),
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, stats: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "label",
                "x",
                "y",
                "width",
                "height",
                "area",
                "coverage_pct",
                "parent_coverage_pct",
                "color",
                "level",
                "parent_id",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in stats["zones"]:
            writer.writerow(row)


def validate_image_reference(specs: dict[str, Any], image_path: Path) -> None:
    expected = specs.get("image")
    if expected and Path(expected).name != image_path.name:
        raise ZoneValidationError(
            "Image filename does not match the 'image' field in zones JSON: "
            f"{expected!r} vs {image_path.name!r}"
        )


def main() -> int:
    args = parse_args()

    try:
        specs = load_zone_specs(args.zones)
        validate_image_reference(specs, args.image)
        zones = load_zones(specs)

        with Image.open(args.image) as image_handle:
            image = image_handle.convert("RGB")
        out_of_bounds = find_out_of_bounds(zones, image.size)
        overlaps = find_overlaps(zones)

        if args.fail_on_bounds and out_of_bounds:
            raise ZoneValidationError(
                "One or more zones exceed image bounds. "
                "Rerun without --fail-on-bounds to inspect stats output."
            )
        if args.fail_on_overlap and overlaps:
            raise ZoneValidationError(
                "One or more zones overlap. "
                "Rerun without --fail-on-overlap to inspect stats output."
            )

        stats = build_stats(args.image.resolve(), image.size, zones, overlaps, out_of_bounds)
        annotated = draw_annotations(image, zones, args.font_size)

        args.output_dir.mkdir(parents=True, exist_ok=True)
        annotated_path = args.output_dir / args.annotated_name
        json_path = args.output_dir / args.json_name
        csv_path = args.output_dir / args.csv_name

        annotated.save(annotated_path)
        write_json(json_path, stats)
        write_csv(csv_path, stats)
    except ZoneValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Annotated image: {annotated_path}")
    print(f"JSON stats: {json_path}")
    print(f"CSV stats: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
