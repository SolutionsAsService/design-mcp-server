from __future__ import annotations

import unittest

from design_mcp.units import convert_quantity, normalize_quantity


class UnitTests(unittest.TestCase):
    def test_explicit_length_area_volume_and_mass(self) -> None:
        for value, source, target, expected in [
            (2500, "mm", "m", 2.5),
            (1, "m2", "mm2", 1_000_000),
            (1_000_000_000, "mm3", "m3", 1),
            (2500, "g", "kg", 2.5),
            (2.5, "kg", "g", 2500),
        ]:
            with self.subTest(source=source, target=target):
                self.assertAlmostEqual(convert_quantity(value, source, target)["value"], expected)
        self.assertEqual(normalize_quantity(9, "V")["canonical_unit"], "V")

    def test_rejects_incompatible_and_nonfinite(self) -> None:
        for value, source, target in [(1, "kg", "m"), (1, "mm", "mm2"),
                                      (True, "mm", "m"), (float("nan"), "mm", "m"),
                                      (float("inf"), "mm", "m"), (1, "yd", "m")]:
            with self.subTest(value=value, source=source, target=target), self.assertRaises(ValueError):
                convert_quantity(value, source, target)


if __name__ == "__main__":
    unittest.main()
