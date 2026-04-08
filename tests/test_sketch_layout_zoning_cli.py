from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "sketch-layout-zoning"
SKETCH = Path(
    os.environ.get("SKETCH_LAYOUT_ZONING_FIXTURE", "")
).expanduser() if os.environ.get("SKETCH_LAYOUT_ZONING_FIXTURE") else None


@unittest.skipUnless(SKETCH and SKETCH.exists(), "Sketch fixture not available")
class SketchLayoutZoningCliTests(unittest.TestCase):
    def test_report_generates_level_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            zones_output = temp / "zones.json"
            json_output = temp / "stats.json"
            csv_output = temp / "stats.csv"
            result = subprocess.run(
                [
                    str(CLI),
                    "report",
                    str(SKETCH),
                    "--zones-output",
                    str(zones_output),
                    "--json-output",
                    str(json_output),
                    "--csv-output",
                    str(csv_output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            stats = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertTrue(zones_output.exists())
            self.assertTrue(csv_output.exists())
            self.assertIn("level_summary", stats)
            self.assertIn("tree", stats)
            self.assertGreaterEqual(len(stats["zones"]), 8)
            child_rows = [zone for zone in stats["zones"] if zone.get("parent_id")]
            self.assertTrue(child_rows)
            self.assertTrue(all("parent_coverage_pct" in row for row in child_rows))


if __name__ == "__main__":
    unittest.main()
