from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from design_mcp.preview import inspect_cad_preview, preview_cad_revision

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"></svg>'


class PreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.revisions = self.root / "revisions"
        self.previews = self.root / "previews"
        self.revisions.mkdir()
        self.previews.mkdir()
        self.python = self.root / "python.exe"
        self.python.write_bytes(b"runtime")
        self.revision_id = "a" * 32
        self.model = self.revisions / f"revision-{self.revision_id}.fcstd"
        self.model.write_bytes(b"model")
        self.manifest = self.revisions / f"revision-{self.revision_id}.json"
        self.manifest.write_text(json.dumps({
            "revision_id": self.revision_id, "model": self.model.name,
            "sha256": hashlib.sha256(b"model").hexdigest(), "operation": "create_box",
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_preview_export_and_hash_linked_reinspection(self) -> None:
        def fake_worker(arguments, **_kwargs):
            Path(arguments[-1]).write_bytes(SVG)
            return type("Result", (), {"returncode": 0, "stderr": "",
                                       "stdout": 'DESIGN_MCP_RESULT={"triangle_count":12}'})()

        with patch("design_mcp.preview.subprocess.run", side_effect=fake_worker) as worker:
            record = preview_cad_revision(self.revisions, self.previews, self.revision_id,
                                          self.python)
        self.assertEqual(worker.call_args.args[0][-3], "preview")
        self.assertEqual(worker.call_args.args[0][-2], "Box")
        self.assertEqual(record["source_sha256"], hashlib.sha256(b"model").hexdigest())
        verified = inspect_cad_preview(self.revisions, self.previews, record["preview_id"])
        self.assertEqual(verified["status"], "HASH_VERIFIED_NOT_VISUALLY_APPROVED")
        (self.previews / record["svg"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            inspect_cad_preview(self.revisions, self.previews, record["preview_id"])

    def test_preview_rejects_invalid_root_and_source_before_worker(self) -> None:
        with patch("design_mcp.preview.subprocess.run") as worker:
            with self.assertRaises(ValueError):
                preview_cad_revision(self.revisions, self.revisions, self.revision_id, self.python)
            self.model.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                preview_cad_revision(self.revisions, self.previews, self.revision_id, self.python)
            worker.assert_not_called()

    def test_preview_failure_cleans_partial_output(self) -> None:
        def fake_worker(arguments, **_kwargs):
            Path(arguments[-1]).write_bytes(b"not-svg")
            return type("Result", (), {"returncode": 0, "stderr": "",
                                       "stdout": 'DESIGN_MCP_RESULT={"triangle_count":12}'})()

        with patch("design_mcp.preview.subprocess.run", side_effect=fake_worker):
            with self.assertRaisesRegex(RuntimeError, "valid SVG"):
                preview_cad_revision(self.revisions, self.previews, self.revision_id, self.python)
        self.assertEqual(list(self.previews.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
