from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from design_mcp.project_snapshot import (create_project_snapshot,
                                         inspect_project_snapshot,
                                         list_project_snapshots)


class ProjectSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.assets = root / "assets"
        self.revisions = root / "revisions"
        self.assets.mkdir()
        self.revisions.mkdir()
        (self.assets / "part.step").write_bytes(b"generic fixture")
        self.revision_id = "a" * 32
        self.model = self.revisions / f"revision-{self.revision_id}.fcstd"
        self.model.write_bytes(b"model")
        manifest = {"revision_id": self.revision_id, "model": self.model.name,
                    "sha256": hashlib.sha256(b"model").hexdigest(),
                    "operation": "create_box"}
        (self.revisions / f"revision-{self.revision_id}.json").write_text(
            json.dumps(manifest), encoding="utf-8")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_snapshot_rechecks_assets_and_cad(self) -> None:
        created = create_project_snapshot(self.assets, self.revisions, "fixture",
                                          ["part.step"], [self.revision_id])
        identifier = created["snapshot_id"]
        report = inspect_project_snapshot(self.assets, self.revisions, identifier)
        self.assertEqual(report["status"], "CURRENT")
        self.assertEqual(report["recheck"], [])
        self.assertEqual(list_project_snapshots(self.revisions)["snapshots"][0]["status"],
                         "HASH_VERIFIED")
        (self.assets / "part.step").write_bytes(b"changed")
        self.model.write_bytes(b"changed model")
        report = inspect_project_snapshot(self.assets, self.revisions, identifier)
        self.assertEqual(report["status"], "STALE")
        self.assertEqual({item["kind"] for item in report["changes"]},
                         {"asset", "cad_revision"})
        self.assertIn("ASSET_INSPECTION", report["recheck"])
        self.assertIn("CAD_INSPECTION", report["recheck"])

    def test_missing_asset_and_unknown_reference(self) -> None:
        created = create_project_snapshot(self.assets, self.revisions, "fixture",
                                          ["part.step"], [])
        (self.assets / "part.step").unlink()
        report = inspect_project_snapshot(self.assets, self.revisions, created["snapshot_id"])
        self.assertEqual(report["status"], "STALE")
        self.assertEqual(report["changes"][0]["status"], "MISSING")
        (self.assets / "part.step").write_bytes(b"restored")
        with patch("design_mcp.project_snapshot.inspect_asset",
                   return_value={"path": "part.step", "size_bytes": 999}):
            report = inspect_project_snapshot(self.assets, self.revisions, created["snapshot_id"])
        self.assertEqual(report["status"], "UNKNOWN")
        self.assertEqual(report["unknowns"][0]["reason"], "SIZE_LIMIT")

    def test_rejects_untrusted_paths_duplicates_and_limits(self) -> None:
        for paths, identifiers in [(["../outside"], []), (["part.step"] * 2, []),
                                   (["part.step"] * 21, []), ([], []),
                                   ([], [self.revision_id] * 2)]:
            with self.subTest(paths=paths, identifiers=identifiers), self.assertRaises(ValueError):
                create_project_snapshot(self.assets, self.revisions, "fixture", paths, identifiers)
        self.assertEqual(list(self.revisions.glob("snapshot-*.json")), [])

    def test_corrupt_manifest_is_not_trusted(self) -> None:
        created = create_project_snapshot(self.assets, self.revisions, "fixture",
                                          ["part.step"], [])
        path = self.revisions / f"snapshot-{created['snapshot_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["assets"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash validation"):
            inspect_project_snapshot(self.assets, self.revisions, created["snapshot_id"])
        self.assertEqual(list_project_snapshots(self.revisions)["snapshots"][0]["status"],
                         "INVALID")
        with self.assertRaises(ValueError):
            inspect_project_snapshot(self.assets, self.revisions, "../path")


if __name__ == "__main__":
    unittest.main()
