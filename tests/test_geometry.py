from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from design_mcp.geometry import get_stl_entities, inspect_stl_geometry


def _ascii_stl(triangles: list[tuple[tuple[float, float, float], ...]]) -> str:
    lines = ["solid test"]
    for triangle in triangles:
        lines.append("facet normal 0 0 0")
        lines.append("outer loop")
        for vertex in triangle:
            lines.append("vertex " + " ".join(format(value, ".9g") for value in vertex))
        lines.extend(["endloop", "endfacet"])
    lines.append("endsolid test")
    return "\n".join(lines) + "\n"


class GeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _write_mesh(self, name: str, triangles: list[tuple[tuple[float, float, float], ...]]) -> None:
        (self.root / name).write_text(_ascii_stl(triangles), encoding="ascii")

    def test_closed_cube_metrics(self) -> None:
        vertices = [
            (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
        ]
        faces = [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (3, 6, 2), (3, 7, 6),
            (0, 4, 7), (0, 7, 3), (1, 6, 5), (1, 2, 6),
        ]
        self._write_mesh("cube.stl", [tuple(vertices[index] for index in face) for face in faces])

        result = inspect_stl_geometry(self.root, "cube.stl")

        self.assertEqual(result["integrity"], "STRUCTURE_VALID")
        self.assertEqual(result["coordinate_units"], "UNKNOWN; STL does not encode units")
        self.assertEqual(result["topology"]["face_count"], 12)
        self.assertEqual(result["topology"]["unique_vertex_count"], 8)
        self.assertEqual(result["topology"]["unique_edge_count"], 18)
        self.assertEqual(result["topology"]["edge_connected_shell_count"], 1)
        self.assertTrue(result["topology"]["closed_consistently_oriented"])
        self.assertEqual(result["bounding_box_model_units"]["extent"], [1.0, 1.0, 1.0])
        self.assertAlmostEqual(result["surface_area_model_units2"], 6.0)
        self.assertAlmostEqual(result["enclosed_volume_model_units3"], 1.0)
        for coordinate in result["volume_centroid_model_units"]:
            self.assertAlmostEqual(coordinate, 0.5)

    def test_open_mesh_does_not_claim_enclosed_volume(self) -> None:
        self._write_mesh("open.stl", [((0, 0, 0), (1, 0, 0), (0, 1, 0))])

        result = inspect_stl_geometry(self.root, "open.stl")

        self.assertEqual(result["integrity"], "STRUCTURE_VALID")
        self.assertEqual(result["enclosed_volume_model_units3"], None)
        self.assertFalse(result["topology"]["closed_consistently_oriented"])
        self.assertGreater(result["topology"]["boundary_edge_count"], 0)

    def test_entity_pages_are_bounded_and_indexed(self) -> None:
        self._write_mesh("triangle.stl", [((0, 0, 0), (1, 0, 0), (0, 1, 0))])

        result = get_stl_entities(self.root, "triangle.stl", "faces", 0, 1)

        self.assertEqual(result["entity_count"], 1)
        self.assertFalse(result["has_more"])
        self.assertEqual(result["entities"][0]["vertices"], [0, 1, 2])

    def test_entity_limit_is_validated(self) -> None:
        self._write_mesh("triangle.stl", [((0, 0, 0), (1, 0, 0), (0, 1, 0))])

        with self.assertRaises(ValueError):
            get_stl_entities(self.root, "triangle.stl", "faces", 0, 501)


if __name__ == "__main__":
    unittest.main()
