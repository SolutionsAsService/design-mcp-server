from __future__ import annotations
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from design_mcp.catalog import inspect_asset, list_assets

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_listing_skips_tooling_directories(self):
        (self.root / "mesh.stl").write_text("solid x\nendsolid x\n", encoding="ascii")
        (self.root / ".git").mkdir()
        (self.root / ".git" / "hidden").write_text("x", encoding="ascii")
        self.assertEqual([x["path"] for x in list_assets(self.root)["assets"]], ["mesh.stl"])

    def test_ascii_stl_and_digest(self):
        data = b"solid x\nfacet normal 0 0 1\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendsolid x\n"
        (self.root / "mesh.stl").write_bytes(data)
        result = inspect_asset(self.root, "mesh.stl")
        self.assertEqual(result["integrity"], "STRUCTURE_VALID")
        self.assertEqual(result["triangle_records"], 1)
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())

    def test_binary_stl_truncated_is_invalid(self):
        data = bytearray(134)
        struct.pack_into("<I", data, 80, 1)
        (self.root / "mesh.stl").write_bytes(bytes(data[:-1]))
        self.assertEqual(inspect_asset(self.root, "mesh.stl")["integrity"], "INVALID")

    def test_step_is_hashed_only(self):
        (self.root / "part.step").write_text("ISO-10303-21;", encoding="ascii")
        self.assertEqual(inspect_asset(self.root, "part.step")["integrity"], "HASHED_ONLY")

    def test_parent_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            inspect_asset(self.root, "../outside")

    def test_unknown_file_is_hashed_only(self):
        (self.root / "note.txt").write_text("note", encoding="utf-8")
        self.assertEqual(inspect_asset(self.root, "note.txt")["integrity"], "HASHED_ONLY")

if __name__ == "__main__":
    unittest.main()
