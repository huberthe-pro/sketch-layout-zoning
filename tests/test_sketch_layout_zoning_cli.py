from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "sketch-layout-zoning"
SKETCH = Path(
    os.environ.get("SKETCH_LAYOUT_ZONING_FIXTURE", "")
).expanduser() if os.environ.get("SKETCH_LAYOUT_ZONING_FIXTURE") else None


@unittest.skipUnless(SKETCH and SKETCH.exists(), "Sketch fixture not available")
class SketchLayoutZoningCliTests(unittest.TestCase):
    def find_first_content_page_name(self) -> str:
        with zipfile.ZipFile(SKETCH) as archive:
            page_names = []
            for name in archive.namelist():
                if name.startswith("pages/") and name.endswith(".json"):
                    page = json.loads(archive.read(name))
                    page_name = str(page.get("name") or "")
                    if page_name not in {"控件", "Symbols"}:
                        page_names.append(page_name)
        self.assertTrue(page_names)
        return page_names[0]

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CLI), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_version_flag(self) -> None:
        result = self.run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout.strip(), r"^sketch-layout-zoning \d+\.\d+\.\d+$")

    def test_report_generates_level_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            zones_output = temp / "zones.json"
            json_output = temp / "stats.json"
            csv_output = temp / "stats.csv"
            result = self.run_cli(
                "report",
                str(SKETCH),
                "--zones-output",
                str(zones_output),
                "--json-output",
                str(json_output),
                "--csv-output",
                str(csv_output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            stats = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertTrue(zones_output.exists())
            self.assertTrue(csv_output.exists())
            self.assertIn("level_summary", stats)
            self.assertIn("tree", stats)
            self.assertGreaterEqual(len(stats["zones"]), 1)
            self.assertEqual(stats["summary"]["zone_count"], len(stats["zones"]))
            child_rows = [zone for zone in stats["zones"] if zone.get("parent_id")]
            self.assertTrue(all("parent_coverage_pct" in row for row in child_rows))
            self.assertGreaterEqual(len(stats["tree"]), 1)
            self.assertTrue(all("coverage_pct" in node for node in stats["zones"]))

    def test_extract_generates_zones_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "zones.json"
            result = self.run_cli(
                "extract",
                str(SKETCH),
                "--output",
                str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("source", payload)
            self.assertIn("zones", payload)
            self.assertGreaterEqual(len(payload["zones"]), 1)
            self.assertTrue(all("level" in zone for zone in payload["zones"]))
            self.assertTrue(all(zone["level"] in {1, 2, 3} for zone in payload["zones"]))

    def test_report_supports_page_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            zones_output = Path(temp_dir) / "zones.json"
            json_output = Path(temp_dir) / "stats.json"
            csv_output = Path(temp_dir) / "stats.csv"
            page_name = self.find_first_content_page_name()
            result = self.run_cli(
                "report",
                str(SKETCH),
                "--page-name",
                page_name,
                "--zones-output",
                str(zones_output),
                "--json-output",
                str(json_output),
                "--csv-output",
                str(csv_output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            stats = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(stats["source"]["page_name"], page_name)

    def test_report_fails_for_missing_root_name(self) -> None:
        result = self.run_cli(
            "report",
            str(SKETCH),
            "--root-name",
            "不存在的分组",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Root layer not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
