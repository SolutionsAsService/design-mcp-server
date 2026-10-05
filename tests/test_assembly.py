from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from design_mcp.assembly import inspect_cad_envelopes


def model_object(name: str, start: list[float] | None) -> dict:
    bounds = None if start is None else {"minimum": start,
                                          "maximum": [start[0] + 2, start[1] + 3, start[2] + 4]}
    return {"name": name, "type": "Part::Box", "parents": [],
            "shape": {"valid": True, "bounding_box_mm": bounds} if bounds else None}


class EnvelopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "fixture.fcstd").write_bytes(b"fixture")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _inspect(self, objects: list[dict], names: list[str], gap: float = 0) -> dict:
        with patch("design_mcp.assembly.inspect_freecad",
                   return_value={"objects": objects, "objects_truncated": False}):
            return inspect_cad_envelopes(self.root, "fixture.fcstd", names, gap)

    def test_separation_lower_bound_not_collision_certification(self) -> None:
        result = self._inspect([model_object("First", [0, 0, 0]),
                                model_object("Second", [4, 0, 0])],
                               ["First", "Second"], 1)
        self.assertEqual(result["pairs"][0]["minimum_distance_lower_bound_mm"], 2)
        self.assertEqual(result["pairs"][0]["status"], "LOWER_BOUND_EXCEEDS_THRESHOLD")
        self.assertEqual(len(result["source_sha256"]), 64)

    def test_overlapping_and_missing_envelopes_remain_unknown(self) -> None:
        objects = [model_object("First", [0, 0, 0]), model_object("Touching", [2, 0, 0]),
                   model_object("Overlapping", [1, 0, 0]), model_object("NoShape", None)]
        result = self._inspect(objects, ["First", "Touching", "Overlapping", "NoShape"])
        self.assertEqual(len(result["pairs"]), 6)
        self.assertEqual({pair["status"] for pair in result["pairs"]}, {"UNKNOWN"})
        self.assertTrue(any(pair["reason"] == "MISSING_OR_INVALID_ENVELOPE"
                            for pair in result["pairs"]))

    def test_input_bounds_and_document_changes_fail_closed(self) -> None:
        for path, names, gap in [("../fixture.fcstd", ["One", "Two"], 0),
                                 ("fixture.fcstd", ["One", "One"], 0),
                                 ("fixture.step", ["One", "Two"], 0),
                                 ("fixture.fcstd", ["One", "Two"], float("nan")),
                                 ("fixture.fcstd", ["One", "Two"], -1)]:
            with self.subTest(path=path, names=names, gap=gap), self.assertRaises(ValueError):
                inspect_cad_envelopes(self.root, path, names, gap)
        with patch("design_mcp.assembly.inspect_freecad", return_value={"objects": [],
                   "objects_truncated": True}):
            with self.assertRaisesRegex(ValueError, "bounded inspection"):
                inspect_cad_envelopes(self.root, "fixture.fcstd", ["One", "Two"])

    def test_source_mutation_during_worker_is_rejected(self) -> None:
        def changed(_root, _relative, _runtime):
            (self.root / "fixture.fcstd").write_bytes(b"changed")
            return {"objects": [], "objects_truncated": False}

        with patch("design_mcp.assembly.inspect_freecad", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "source changed"):
                inspect_cad_envelopes(self.root, "fixture.fcstd", ["One", "Two"])


if __name__ == "__main__":
    unittest.main()
