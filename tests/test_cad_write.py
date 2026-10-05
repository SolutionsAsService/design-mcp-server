from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from design_mcp.cad_write import (compare_box_revisions, create_box_revision,
                                  inspect_revision, list_revisions, revise_box_parameters,
                                  rollback_box_revision)


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

    def test_copy_on_write_revision_and_comparison(self) -> None:
        def fake_worker(arguments, **_kwargs):
            dimensions = [float(value) for value in arguments[-3:]]
            Path(arguments[3]).write_bytes(repr(dimensions).encode("ascii"))
            geometry = {"shape": {"valid": True, "closed": True, "solids": 1,
                                  "bounding_box_mm": {"extent": dimensions}}}
            return type("Result", (), {"returncode": 0, "stderr": "",
                                       "stdout": "DESIGN_MCP_RESULT=" + json.dumps(geometry)})()

        with patch("design_mcp.cad_write.subprocess.run", side_effect=fake_worker) as runner:
            parent = create_box_revision(self.root, 2, 3, 4, self.python)
            child = revise_box_parameters(self.root, parent["revision_id"], 5, 3, 4, self.python)
        self.assertEqual(runner.call_args.args[0][4], "revise_box")
        self.assertEqual(runner.call_args.args[0][5], str(self.root / parent["model"]))
        self.assertEqual(child["parent_revision_id"], parent["revision_id"])
        self.assertEqual(child["parent_sha256"], parent["sha256"])
        comparison = compare_box_revisions(self.root, parent["revision_id"], child["revision_id"])
        self.assertTrue(comparison["is_direct_child"])
        self.assertEqual(comparison["dimensions_mm"]["length"],
                         {"before": 2, "after": 5, "change": 3})
        self.assertEqual((self.root / parent["model"]).read_bytes(), b"[2.0, 3.0, 4.0]")
        (self.root / parent["model"]).write_bytes(b"tampered")
        with patch("design_mcp.cad_write.subprocess.run") as blocked:
            with self.assertRaises(ValueError):
                revise_box_parameters(self.root, parent["revision_id"], 6, 3, 4, self.python)
            blocked.assert_not_called()

    def test_rejects_worker_mutation_of_parent(self) -> None:
        geometry = {"shape": {"valid": True, "closed": True, "solids": 1,
                              "bounding_box_mm": {"extent": [2, 3, 4]}}}

        def create_worker(arguments, **_kwargs):
            Path(arguments[3]).write_bytes(b"original")
            return type("Result", (), {"returncode": 0, "stderr": "",
                                       "stdout": "DESIGN_MCP_RESULT=" + json.dumps(geometry)})()

        with patch("design_mcp.cad_write.subprocess.run", side_effect=create_worker):
            parent = create_box_revision(self.root, 2, 3, 4, self.python)

        def mutating_worker(arguments, **_kwargs):
            Path(arguments[5]).write_bytes(b"changed parent")
            Path(arguments[3]).write_bytes(b"child")
            return type("Result", (), {"returncode": 0, "stderr": "",
                                       "stdout": "DESIGN_MCP_RESULT=" + json.dumps(geometry)})()

        with patch("design_mcp.cad_write.subprocess.run", side_effect=mutating_worker):
            with self.assertRaisesRegex(RuntimeError, "Source revision changed"):
                revise_box_parameters(self.root, parent["revision_id"], 2, 3, 4, self.python)
        self.assertEqual(len(list(self.root.glob("revision-*.fcstd"))), 1)
        self.assertEqual(len(list(self.root.glob("revision-*.json"))), 1)

    def test_rollback_creates_child_and_keeps_ancestors(self) -> None:
        def fake_worker(arguments, **_kwargs):
            dimensions = [float(value) for value in arguments[-3:]]
            Path(arguments[3]).write_bytes(repr(dimensions).encode("ascii"))
            geometry = {"shape": {"valid": True, "closed": True, "solids": 1,
                                  "bounding_box_mm": {"extent": dimensions}}}
            return type("Result", (), {"returncode": 0, "stderr": "",
                                       "stdout": "DESIGN_MCP_RESULT=" + json.dumps(geometry)})()

        def fake_inspection(_root, filename, _python):
            values = json.loads((self.root / filename).read_bytes().decode("ascii"))
            return {"objects": [{"shape": {"valid": True, "closed": True,
                                            "solids": 1, "bounding_box_mm": {"extent": values}}}]}

        with (patch("design_mcp.cad_write.subprocess.run", side_effect=fake_worker),
              patch("design_mcp.cad_write.inspect_freecad", side_effect=fake_inspection)):
            first = create_box_revision(self.root, 2, 3, 4, self.python)
            second = revise_box_parameters(self.root, first["revision_id"], 5, 3, 4, self.python)
            third = revise_box_parameters(self.root, second["revision_id"], 6, 3, 4, self.python)
            reverted = rollback_box_revision(self.root, third["revision_id"], first["revision_id"], self.python)
            again = revise_box_parameters(self.root, reverted["revision_id"], 7, 3, 4, self.python)
        self.assertEqual(reverted["operation"], "rollback_box")
        self.assertEqual(reverted["parent_revision_id"], third["revision_id"])
        self.assertEqual(reverted["rollback_target_revision_id"], first["revision_id"])
        self.assertEqual(reverted["rollback_target_sha256"], first["sha256"])
        self.assertEqual(reverted["dimensions_mm"], first["dimensions_mm"])
        self.assertEqual(again["parent_revision_id"], reverted["revision_id"])
        self.assertEqual((self.root / third["model"]).read_bytes(), b"[6.0, 3.0, 4.0]")
        with self.assertRaisesRegex(ValueError, "earlier ancestor"):
            rollback_box_revision(self.root, third["revision_id"], third["revision_id"], self.python)
        with self.assertRaisesRegex(ValueError, "not a verified ancestor"):
            rollback_box_revision(self.root, first["revision_id"], second["revision_id"], self.python)

        target_manifest = self.root / f"revision-{first['revision_id']}.json"
        original_target = target_manifest.read_text(encoding="utf-8")
        target_record = json.loads(original_target)
        target_record["dimensions_mm"]["length"] = 9
        target_manifest.write_text(json.dumps(target_record), encoding="utf-8")
        with (patch("design_mcp.cad_write.inspect_freecad", side_effect=fake_inspection),
              patch("design_mcp.cad_write.subprocess.run") as blocked):
            with self.assertRaisesRegex(ValueError, "does not match recorded dimensions"):
                rollback_box_revision(self.root, third["revision_id"], first["revision_id"], self.python)
            blocked.assert_not_called()
        target_manifest.write_text(original_target, encoding="utf-8")

        manifest_path = self.root / f"revision-{third['revision_id']}.json"
        record = json.loads(manifest_path.read_text(encoding="utf-8"))
        record["parent_sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(record), encoding="utf-8")
        with patch("design_mcp.cad_write.subprocess.run") as blocked:
            with self.assertRaisesRegex(ValueError, "lineage hash mismatch"):
                rollback_box_revision(self.root, third["revision_id"], first["revision_id"], self.python)
            blocked.assert_not_called()

    def test_revision_index_paginates_and_flags_corruption(self) -> None:
        revision_ids = ["0" * 32, "1" * 32, "2" * 32]
        for revision_id in revision_ids:
            model_name = f"revision-{revision_id}.fcstd"
            data = revision_id.encode("ascii")
            (self.root / model_name).write_bytes(data)
            record = {"revision_id": revision_id, "model": model_name,
                      "sha256": hashlib.sha256(data).hexdigest(), "operation": "create_box",
                      "dimensions_mm": {"length": 2, "width": 3, "height": 4},
                      "validation": "REOPENED_GEOMETRY_ONLY"}
            (self.root / f"revision-{revision_id}.json").write_text(json.dumps(record), encoding="utf-8")
        (self.root / f"revision-{revision_ids[1]}.fcstd").write_bytes(b"changed")
        first_page = list_revisions(self.root, 0, 2)
        self.assertEqual(first_page["total"], 3)
        self.assertTrue(first_page["has_more"])
        self.assertEqual([item["status"] for item in first_page["revisions"]],
                         ["HASH_VERIFIED", "INVALID"])
        last_page = list_revisions(self.root, 2, 2)
        self.assertFalse(last_page["has_more"])
        self.assertEqual(last_page["revisions"][0]["revision_id"], revision_ids[2])
        with self.assertRaises(ValueError):
            list_revisions(self.root, -1, 2)
        with self.assertRaises(ValueError):
            list_revisions(self.root, 0, 21)


if __name__ == "__main__":
    unittest.main()
