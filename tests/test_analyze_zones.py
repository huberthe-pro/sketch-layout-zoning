from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app-layout-zoning" / "scripts" / "analyze_zones.py"


@unittest.skipUnless(Image is not None, "Pillow not installed")
class AnalyzeZonesTests(unittest.TestCase):
    def run_script(self, image_path: Path, zones_path: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(image_path), str(zones_path), *extra_args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def make_image(self, path: Path, size: tuple[int, int] = (100, 200)) -> None:
        Image.new("RGB", size, color=(255, 255, 255)).save(path)

    def test_generates_outputs_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "image.png"
            zones_path = temp_path / "zones.json"
            output_dir = temp_path / "out"
            self.make_image(image_path)
            zones_path.write_text(
                json.dumps(
                    {
                        "image": "image.png",
                        "zones": [
                            {
                                "id": "top",
                                "label": "顶部区域",
                                "x": 0,
                                "y": 0,
                                "width": 100,
                                "height": 80,
                            },
                            {
                                "id": "bottom",
                                "label": "底部区域",
                                "x": 0,
                                "y": 80,
                                "width": 100,
                                "height": 120,
                                "color": "#123456",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = self.run_script(image_path, zones_path, "--output-dir", str(output_dir))

            self.assertEqual(result.returncode, 0, result.stderr)
            stats = json.loads((output_dir / "stats.json").read_text(encoding="utf-8"))
            self.assertTrue((output_dir / "annotated.png").exists())
            self.assertTrue((output_dir / "stats.csv").exists())
            self.assertEqual(stats["summary"]["coverage_pct"], 100.0)
            self.assertEqual(stats["summary"]["uncovered_pct"], 0.0)
            self.assertEqual(stats["zones"][0]["coverage_pct"], 40.0)
            self.assertEqual(stats["zones"][1]["coverage_pct"], 60.0)
            self.assertEqual(stats["zones"][0]["color"], "#FF8A00")

    def test_fail_on_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "image.png"
            zones_path = temp_path / "zones.json"
            self.make_image(image_path)
            zones_path.write_text(
                json.dumps(
                    {
                        "zones": [
                            {
                                "id": "one",
                                "label": "一区",
                                "x": 0,
                                "y": 0,
                                "width": 70,
                                "height": 100,
                            },
                            {
                                "id": "two",
                                "label": "二区",
                                "x": 50,
                                "y": 10,
                                "width": 50,
                                "height": 100,
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = self.run_script(image_path, zones_path, "--fail-on-overlap")

            self.assertEqual(result.returncode, 2)
            self.assertIn("overlap", result.stderr.lower())

    def test_fail_on_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "image.png"
            zones_path = temp_path / "zones.json"
            self.make_image(image_path)
            zones_path.write_text(
                json.dumps(
                    {
                        "zones": [
                            {
                                "id": "hero",
                                "label": "头图",
                                "x": 0,
                                "y": 0,
                                "width": 120,
                                "height": 80,
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = self.run_script(image_path, zones_path, "--fail-on-bounds")

            self.assertEqual(result.returncode, 2)
            self.assertIn("bounds", result.stderr.lower())

    def test_includes_level_and_parent_percentages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            image_path = temp_path / "image.png"
            zones_path = temp_path / "zones.json"
            output_dir = temp_path / "out"
            self.make_image(image_path, (100, 100))
            zones_path.write_text(
                json.dumps(
                    {
                        "zones": [
                            {
                                "id": "root",
                                "label": "一级",
                                "x": 0,
                                "y": 0,
                                "width": 100,
                                "height": 50,
                                "level": 1,
                            },
                            {
                                "id": "child",
                                "label": "二级",
                                "x": 0,
                                "y": 0,
                                "width": 50,
                                "height": 50,
                                "level": 2,
                                "parent_id": "root",
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = self.run_script(image_path, zones_path, "--output-dir", str(output_dir))

            self.assertEqual(result.returncode, 0, result.stderr)
            stats = json.loads((output_dir / "stats.json").read_text(encoding="utf-8"))
            root_zone = next(zone for zone in stats["zones"] if zone["id"] == "root")
            child_zone = next(zone for zone in stats["zones"] if zone["id"] == "child")
            self.assertEqual(root_zone["coverage_pct"], 50.0)
            self.assertEqual(child_zone["coverage_pct"], 25.0)
            self.assertEqual(child_zone["parent_coverage_pct"], 50.0)
            self.assertEqual(stats["level_summary"]["1"]["coverage_pct"], 50.0)
            self.assertEqual(stats["level_summary"]["2"]["coverage_pct"], 25.0)


if __name__ == "__main__":
    unittest.main()
