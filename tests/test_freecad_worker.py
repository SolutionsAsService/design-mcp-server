from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class Vector:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x, self.y, self.z = x, y, z


class Solid:
    def __init__(self, volume: float, center: Vector) -> None:
        self.Volume = volume
        self.CenterOfMass = center

    def isValid(self) -> bool:
        return True

    def isClosed(self) -> bool:
        return True


class Shape:
    def __init__(self, distance: float, overlap_volume: float, solid: bool = True) -> None:
        self.distance = distance
        self.overlap_volume = overlap_volume
        self.Solids = [Solid(24, Vector(1, 1.5, 2))] if solid else []

    def isNull(self) -> bool:
        return False

    def isValid(self) -> bool:
        return True

    def isClosed(self) -> bool:
        return True

    def distToShape(self, other: Shape) -> tuple:
        return self.distance, [(Vector(0, 0, 0), Vector(self.distance, 0, 0))], []

    def common(self, other: Shape) -> types.SimpleNamespace:
        return types.SimpleNamespace(isValid=lambda: True, Volume=self.overlap_volume)


class FreeCADWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        freecad = types.ModuleType("FreeCAD")
        part = types.ModuleType("Part")
        cls.document = types.SimpleNamespace(Name="Fixture")
        cls.document.getObject = lambda name: cls.objects.get(name)
        freecad.openDocument = lambda path, hidden: cls.document
        freecad.closeDocument = lambda name: None
        path = Path(__file__).parents[1] / "design_mcp" / "freecad_worker.py"
        spec = importlib.util.spec_from_file_location("freecad_worker_test", path)
        assert spec is not None and spec.loader is not None
        cls.worker = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"FreeCAD": freecad, "Part": part}):
            spec.loader.exec_module(cls.worker)

    def test_distance_distinguishes_volume_overlap_from_zero_distance(self) -> None:
        for distance, volume, expected in [
            (2, 0, "SEPARATED"),
            (0, 0, "ZERO_DISTANCE_NO_VOLUME_OVERLAP"),
            (0, 6, "VOLUMETRIC_OVERLAP"),
        ]:
            with self.subTest(expected=expected):
                self.__class__.objects = {
                    "First": types.SimpleNamespace(Shape=Shape(distance, volume)),
                    "Second": types.SimpleNamespace(Shape=Shape(distance, volume)),
                }
                result = self.worker.measure_distance("fixture.fcstd", "First", "Second")
                self.assertEqual(result["relationship"], expected)
                self.assertEqual(result["intersection_volume_mm3"], volume if distance == 0 else None)

    def test_zero_distance_non_solid_is_unknown(self) -> None:
        self.__class__.objects = {
            "First": types.SimpleNamespace(Shape=Shape(0, 0, solid=False)),
            "Second": types.SimpleNamespace(Shape=Shape(0, 0)),
        }
        result = self.worker.measure_distance("fixture.fcstd", "First", "Second")
        self.assertEqual(result["relationship"], "UNKNOWN_ZERO_DISTANCE_NON_SOLID")
        self.assertIsNone(result["intersection_volume_mm3"])

    def test_compound_centroid_uses_solid_volumes(self) -> None:
        bounds = types.SimpleNamespace(XMin=0, YMin=0, ZMin=0, XMax=4, YMax=2,
                                       ZMax=2, XLength=4, YLength=2, ZLength=2)
        compound = types.SimpleNamespace(
            isNull=lambda: False, isValid=lambda: True, isClosed=lambda: True,
            BoundBox=bounds, Faces=[], Edges=[], Vertexes=[], Shells=[],
            Solids=[Solid(2, Vector(1, 0, 0)), Solid(8, Vector(3, 0, 0))],
            Volume=10, Area=24,
        )
        summary = self.worker._shape_summary(compound)
        self.assertEqual(summary["volume_centroid_mm"], [2.6, 0, 0])


if __name__ == "__main__":
    unittest.main()
