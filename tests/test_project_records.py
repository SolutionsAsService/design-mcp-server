from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from design_mcp.project_records import (add_project_evidence, create_project_record,
                                        inspect_project_record, list_project_records)
from design_mcp.project_snapshot import create_project_snapshot


class ProjectRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        base = Path(self.directory.name)
        self.assets = base / "assets"
        self.revisions = base / "revisions"
        self.assets.mkdir()
        self.revisions.mkdir()
        (self.assets / "drawing.txt").write_bytes(b"generic drawing")
        self.revision_id = "b" * 32
        self.model = self.revisions / f"revision-{self.revision_id}.fcstd"
        self.model.write_bytes(b"generic model")
        (self.revisions / f"revision-{self.revision_id}.json").write_text(
            json.dumps({"revision_id": self.revision_id, "model": self.model.name,
                        "sha256": hashlib.sha256(self.model.read_bytes()).hexdigest()}),
            encoding="utf-8")
        self.snapshot = create_project_snapshot(self.assets, self.revisions, "fixture",
                                                ["drawing.txt"], [self.revision_id])

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _project(self) -> dict:
        return create_project_record(self.assets, self.revisions, "Widget", "Generic fixture",
                                     self.snapshot["snapshot_id"])

    def _evidence(self, project_id: str, **overrides) -> dict:
        fields = {"project_id": project_id, "subject_kind": "cad_revision",
                  "subject_reference": self.revision_id, "source_asset_path": "drawing.txt",
                  "claim": "Drawing notes a dimension", "evidence_status": "MEASURED",
                  "value": 2.5, "unit": "mm"}
        fields.update(overrides)
        return add_project_evidence(self.assets, self.revisions, **fields)

    def test_immutable_project_lineage_and_relationships(self) -> None:
        initial = self._project()
        updated = self._evidence(initial["project_id"])
        self.assertNotEqual(updated["project_id"], initial["project_id"])
        self.assertEqual(updated["parent_project_id"], initial["project_id"])
        self.assertEqual(initial["evidence"], [])
        link = updated["evidence"][0]
        self.assertEqual(link["verification"], "USER_ATTESTED_NOT_INDEPENDENTLY_CHECKED")
        self.assertEqual((link["subject_kind"], link["source_asset_path"]),
                         ("cad_revision", "drawing.txt"))
        report = inspect_project_record(self.assets, self.revisions, updated["project_id"])
        self.assertEqual(report["snapshot_status"], "CURRENT")
        self.assertEqual(report["relationships"][0]["status"],
                         "CONTENT_UNCHANGED_NOT_VERIFIED")
        self.assertEqual(list_project_records(self.revisions)["total"], 2)
        (self.assets / "drawing.txt").write_bytes(b"changed source")
        report = inspect_project_record(self.assets, self.revisions, updated["project_id"])
        self.assertEqual(report["snapshot_status"], "STALE")
        self.assertEqual(report["relationships"][0]["status"], "RECHECK")
        with self.assertRaisesRegex(ValueError, "CURRENT snapshot"):
            self._evidence(updated["project_id"])

    def test_bad_evidence_and_units_fail_before_write(self) -> None:
        initial = self._project()
        for override in [{"subject_reference": "nonexistent"},
                         {"source_asset_path": "../escape"},
                         {"unit": None}, {"value": float("nan")},
                         {"unit": "furlongs"}, {"evidence_status": "AUTO_VERIFIED"}]:
            with self.subTest(override=override), self.assertRaises(ValueError):
                self._evidence(initial["project_id"], **override)
        self.assertEqual(list_project_records(self.revisions)["total"], 1)

    def test_parent_and_snapshot_hash_mismatch_fail_closed(self) -> None:
        initial = self._project()
        updated = self._evidence(initial["project_id"])
        path = self.revisions / f"project-{initial['project_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["name"] = "Tampered"
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash validation"):
            inspect_project_record(self.assets, self.revisions, updated["project_id"])
        self.assertEqual(list_project_records(self.revisions)["total"], 2)
        self.assertIn("INVALID", [entry["status"] for entry in
                                  list_project_records(self.revisions)["projects"]])

    def test_missing_snapshot_reference_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            create_project_record(self.assets, self.revisions, "Fixture", "", "not-an-id")
        initial = self._project()
        snapshot_path = self.revisions / f"snapshot-{self.snapshot['snapshot_id']}.json"
        record = json.loads(snapshot_path.read_text(encoding="utf-8"))
        record["name"] = "Changed"
        snapshot_path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash validation"):
            inspect_project_record(self.assets, self.revisions, initial["project_id"])


if __name__ == "__main__":
    unittest.main()
