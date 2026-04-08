from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app-layout-zoning" / "scripts" / "extract_sketch_zones.py"
SKETCH = Path(
    os.environ.get("SKETCH_LAYOUT_ZONING_FIXTURE", "")
).expanduser() if os.environ.get("SKETCH_LAYOUT_ZONING_FIXTURE") else None


@unittest.skipUnless(SKETCH and SKETCH.exists(), "Sketch fixture not available")
class ExtractSketchZonesTests(unittest.TestCase):
    def test_extracts_multi_level_zones(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "zones.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(SKETCH),
                    "--output",
                    str(output),
                    "--max-depth",
                    "3",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(payload["zones"]), 8)
            levels = {zone["level"] for zone in payload["zones"]}
            self.assertIn(1, levels)
            self.assertIn(2, levels)
            self.assertIn(3, levels)
            labels = {zone["label"] for zone in payload["zones"]}
            self.assertIn("头部", labels)
            self.assertIn("底部导航", labels)


if __name__ == "__main__":
    unittest.main()
