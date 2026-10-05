from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from design_mcp.cad_write import create_box_revision, inspect_revision


class CadRevisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.python = self.root / "python.exe"
        self.python.write_bytes(b"fixture")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_invalid_dimensions_never_launch_worker(self) -> None:
        with patch("design_mcp.cad_write.subprocess.run") as runner:
            for dimensions in [(0, 2, 3), (-1, 2, 3), (True, 2, 3),
                               (float("nan"), 2, 3), (10001, 2, 3)]:
                with self.assertRaises(ValueError):
                    create_box_revision(self.root, *dimensions, self.python)
            runner.assert_not_called()

    def test_creates_hash_manifest_and_inspects_revision(self) -> None:
        geometry = {"format": "FCStd", "shape": {"valid": True, "closed": True, "solids": 1,
                                                  "bounding_box_mm": {"extent": [2, 3, 4]}}}

        def fake_worker(arguments, **_kwargs):
            Path(arguments[3]).write_bytes(b"generated document")
            return type("Result", (), {"returncode": 0,
                                       "stdout": "DESIGN_MCP_RESULT=" + json.dumps(geometry), "stderr": ""})()

        with patch("design_mcp.cad_write.subprocess.run", side_effect=fake_worker):
            record = create_box_revision(self.root, 2, 3, 4, self.python)
        self.assertEqual(record["validation"], "REOPENED_GEOMETRY_ONLY")
        self.assertEqual(record["dimensions_mm"], {"length": 2, "width": 3, "height": 4})
        self.assertTrue((self.root / record["model"]).is_file())
        self.assertEqual(len(list(self.root.glob("revision-*.json"))), 1)
        with patch("design_mcp.cad_write.inspect_freecad", return_value={"objects": []}) as inspector:
            result = inspect_revision(self.root, record["revision_id"], self.python)
        self.assertEqual(result["revision"], record)
        inspector.assert_called_once()
        (self.root / record["model"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            inspect_revision(self.root, record["revision_id"], self.python)

    def test_failure_cleans_output_and_does_not_emit_manifest(self) -> None:
        def fake_worker(arguments, **_kwargs):
            Path(arguments[3]).write_bytes(b"invalid")
            return type("Result", (), {"returncode": 1, "stdout": "", "stderr": "failed"})()

        with patch("design_mcp.cad_write.subprocess.run", side_effect=fake_worker):
            with self.assertRaises(RuntimeError):
                create_box_revision(self.root, 2, 3, 4, self.python)
        self.assertEqual(list(self.root.glob("revision-*")), [])

    def test_rejects_symlink_root_and_invalid_revision_id(self) -> None:
        with patch("design_mcp.cad_write.Path.is_symlink", return_value=True):
            with self.assertRaises(ValueError):
                create_box_revision(self.root, 2, 3, 4, self.python)
        for revision_id in ["../other", "a" * 31, "A" * 32]:
            with self.assertRaises(ValueError):
                inspect_revision(self.root, revision_id, self.python)


if __name__ == "__main__":
    unittest.main()
