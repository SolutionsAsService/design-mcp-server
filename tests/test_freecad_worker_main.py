"""The worker must survive FreeCAD builds whose first `import FreeCAD` replaces __main__ globals.

FreeCAD 26.3 (conda-forge, Linux) runs its init scripts in __main__ on the first import and the
script's earlier stdlib imports disappear (json/math NameError). The fake FreeCAD module below
reproduces that behaviour, so the regression is caught without a FreeCAD install. When
DESIGN_MCP_FREECAD_PYTHON points at a real FreeCAD Python, the worker is also run there.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKER = Path(__file__).parents[1] / "design_mcp" / "freecad_worker.py"

FAKE_FREECAD = '''
import sys
main = sys.modules["__main__"].__dict__
for key in [k for k in main if not k.startswith("__")]:
    del main[key]  # what FreeCAD 26.3's init does to the importing script
'''

FAKE_PART = '''
class _Null:
    def isNull(self):
        return True


def read(path):
    return _Null()
'''


def _payload(stdout: str) -> dict:
    prefix = "DESIGN_MCP_RESULT="
    return json.loads(next(line[len(prefix):] for line in stdout.splitlines() if line.startswith(prefix)))


class WorkerMainGlobalsTests(unittest.TestCase):
    def test_worker_runs_when_freecad_import_clears_main_globals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy(WORKER, folder / "freecad_worker.py")
            (folder / "FreeCAD.py").write_text(FAKE_FREECAD, encoding="utf-8")
            (folder / "Part.py").write_text(FAKE_PART, encoding="utf-8")
            (folder / "part.step").write_text("ISO-10303-21;", encoding="utf-8")
            # Not -I (it drops the script directory from sys.path); -E -s still ignore the environment
            # and user site, and the script directory puts the fakes ahead of any real FreeCAD.
            result = subprocess.run([sys.executable, "-E", "-s", str(folder / "freecad_worker.py"), str(folder / "part.step"), "inspect"],
                                    capture_output=True, text=True, timeout=60, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(_payload(result.stdout)["format"], "STEP")

    @unittest.skipUnless(os.environ.get("DESIGN_MCP_FREECAD_PYTHON"), "set DESIGN_MCP_FREECAD_PYTHON to a real FreeCAD Python")
    def test_worker_runs_in_real_freecad_python(self) -> None:
        python = os.environ["DESIGN_MCP_FREECAD_PYTHON"]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "box.FCStd"
            result = subprocess.run([python, "-I", str(WORKER), str(target), "create_box", "10", "20", "5"],
                                    capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            result = subprocess.run([python, "-I", str(WORKER), str(target), "inspect"],
                                    capture_output=True, text=True, timeout=120, check=False)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            shape = _payload(result.stdout)["objects"][0]["shape"]
            self.assertAlmostEqual(shape["enclosed_volume_mm3"], 1000.0, places=6)
            self.assertEqual([round(v, 9) for v in shape["volume_centroid_mm"]], [5.0, 10.0, 2.5])


if __name__ == "__main__":
    unittest.main()
