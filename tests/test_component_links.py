from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from design_mcp.component_links import (create_assembly_manifest,
                                        inspect_assembly_manifest,
                                        inspect_component_candidate,
                                        list_assembly_manifests,
                                        list_component_candidates,
                                        register_component_candidate)


PART = {"lcsc": "C25804", "model": "0603WAF1002T5E",
        "manufacturer": "UNI-ROYAL(Uniroyal Elec)", "package": "0603"}
FOOTPRINT = {"library": "Resistor_SMD", "name": "R_0603_1608Metric",
             "full_name": "Resistor_SMD:R_0603_1608Metric", "pad_count": 2}


class ComponentLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_candidate_is_unverified_and_missing_envelope_is_unknown(self) -> None:
        candidate = register_component_candidate(self.root, PART, FOOTPRINT)
        record = inspect_component_candidate(self.root, candidate["candidate_id"])
        self.assertEqual(record["geometry_status"], "UNKNOWN")
        self.assertEqual(record["compatibility_status"], "UNKNOWN")
        self.assertEqual(candidate["part"]["mpn"], PART["model"])
        self.assertEqual(candidate["footprint"]["library_id"], FOOTPRINT["full_name"])
        self.assertEqual(list_component_candidates(self.root)["total"], 1)

    def test_hierarchy_preserves_candidate_links_without_fit_claim(self) -> None:
        candidate = register_component_candidate(self.root, PART, FOOTPRINT)
        identifier = candidate["candidate_id"]
        instances = [{"reference": "Root", "candidate_id": identifier,
                      "position_mm": [0, 0, 0]},
                     {"reference": "Child", "candidate_id": identifier,
                      "parent_reference": "Root", "position_mm": [4, 0, 0]}]
        assembly = create_assembly_manifest(self.root, "generic fixture", instances)
        report = inspect_assembly_manifest(self.root, assembly["assembly_id"])
        self.assertEqual(report["reference_status"], "HASHES_CURRENT")
        self.assertEqual(report["fit_status"], "UNKNOWN_MISSING_SOURCE_BACKED_ENVELOPES")
        self.assertEqual(report["assembly"]["instances"][1]["parent_reference"], "Root")
        self.assertEqual(report["assembly"]["instances"][0]["candidate_sha256"],
                         candidate["manifest_sha256"])
        self.assertEqual(list_assembly_manifests(self.root)["total"], 1)
        path = self.root / f"candidate-{identifier}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["part"]["mpn"] = "tampered"
        path.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(inspect_assembly_manifest(self.root, assembly["assembly_id"])
                         ["reference_status"], "UNKNOWN")

    def test_missing_candidate_is_stale(self) -> None:
        candidate = register_component_candidate(self.root, PART, FOOTPRINT)
        assembly = create_assembly_manifest(self.root, "fixture", [
            {"reference": "Only", "candidate_id": candidate["candidate_id"],
             "position_mm": [0, 0, 0]}])
        (self.root / f"candidate-{candidate['candidate_id']}.json").unlink()
        report = inspect_assembly_manifest(self.root, assembly["assembly_id"])
        self.assertEqual(report["reference_status"], "STALE")
        self.assertEqual(report["stale_instances"], ["Only"])

    def test_rejects_invalid_provider_pairing_and_hierarchy(self) -> None:
        with self.assertRaises(ValueError):
            register_component_candidate(self.root, PART, {**FOOTPRINT, "full_name": "wrong"})
        self.assertEqual(list_component_candidates(self.root)["total"], 0)
        candidate = register_component_candidate(self.root, PART, FOOTPRINT)
        identifier = candidate["candidate_id"]
        for instances in [
            [{"reference": "A", "candidate_id": identifier,
              "parent_reference": "B", "position_mm": [0, 0, 0]}],
            [{"reference": "A", "candidate_id": identifier,
              "parent_reference": "B", "position_mm": [0, 0, 0]},
             {"reference": "B", "candidate_id": identifier,
              "parent_reference": "A", "position_mm": [0, 0, 0]}],
            [{"reference": "A", "candidate_id": identifier, "position_mm": [float("nan"), 0, 0]}],
        ]:
            with self.subTest(instances=instances), self.assertRaises(ValueError):
                create_assembly_manifest(self.root, "fixture", instances)

    def test_corrupt_assembly_manifest_is_rejected(self) -> None:
        candidate = register_component_candidate(self.root, PART, FOOTPRINT)
        assembly = create_assembly_manifest(self.root, "fixture", [
            {"reference": "Only", "candidate_id": candidate["candidate_id"],
             "position_mm": [0, 0, 0]}])
        path = self.root / f"assembly-{assembly['assembly_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["instances"][0]["position_mm"] = [999, 0, 0]
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash validation"):
            inspect_assembly_manifest(self.root, assembly["assembly_id"])


if __name__ == "__main__":
    unittest.main()
