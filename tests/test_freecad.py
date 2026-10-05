from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from design_mcp.freecad import inspect_freecad


class FreeCADAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "sample.step").write_text("sample", encoding="ascii")
        (self.root / "python.exe").write_text("fake", encoding="ascii")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_restricts_paths_before_running_freecad(self) -> None:
        with patch("design_mcp.freecad.subprocess.run") as runner:
            with self.assertRaises(ValueError):
                inspect_freecad(self.root, "../sample.step", self.root / "python.exe")
            with self.assertRaises(ValueError):
                inspect_freecad(self.root, "python.exe", self.root / "python.exe")
            runner.assert_not_called()

    def test_returns_structured_worker_result(self) -> None:
        reply = 'DESIGN_MCP_RESULT={"format":"STEP","objects":[]}\n'
        with patch("design_mcp.freecad.subprocess.run") as runner:
            runner.return_value.stdout = reply
            runner.return_value.returncode = 0
            result = inspect_freecad(self.root, "sample.step", self.root / "python.exe")
        self.assertEqual(result["units"]["length"], "mm")
        self.assertEqual(result["format"], "STEP")
        self.assertEqual(runner.call_args.kwargs["timeout"], 60)
        self.assertEqual(runner.call_args.args[0][-1], str(self.root / "sample.step"))

    def test_rejects_missing_runtime(self) -> None:
        with self.assertRaises(RuntimeError):
            inspect_freecad(self.root, "sample.step", self.root / "missing-python.exe")


if __name__ == "__main__":
    unittest.main()
