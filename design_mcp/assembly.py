"""Conservative FCStd envelope checks; no inference of actual collision or fit."""

from __future__ import annotations

import math
from pathlib import Path

from design_mcp.catalog import inspect_asset
from design_mcp.freecad import inspect_freecad

MAX_OBJECTS = 8


def _bounds(shape: dict | None) -> tuple[list[float], list[float]] | None:
    if not isinstance(shape, dict) or shape.get("valid") is not True:
        return None
    bounds = shape.get("bounding_box_mm")
    if not isinstance(bounds, dict):
        return None
    minimum, maximum = bounds.get("minimum"), bounds.get("maximum")
    if (not isinstance(minimum, list) or not isinstance(maximum, list)
            or len(minimum) != 3 or len(maximum) != 3
            or any(isinstance(coordinate, bool) or not isinstance(coordinate, (int, float))
                   or not math.isfinite(coordinate) for coordinate in minimum + maximum)
            or any(low > high for low, high in zip(minimum, maximum))):
        return None
    return minimum, maximum


def inspect_cad_envelopes(asset_root: str | Path, relative_path: str,
                          object_names: list[str], minimum_gap_mm: float = 0,
                          python_executable: str | Path | None = None) -> dict:
    if Path(relative_path).suffix.lower() != ".fcstd":
        raise ValueError("Envelope inspection requires an FCStd document.")
    if (not isinstance(object_names, list) or not 2 <= len(object_names) <= MAX_OBJECTS
            or any(not isinstance(name, str) or not 1 <= len(name) <= 128
                   for name in object_names) or len(set(object_names)) != len(object_names)):
        raise ValueError("Select 2–8 distinct FCStd object names, at most 128 characters each.")
    if (isinstance(minimum_gap_mm, bool) or not isinstance(minimum_gap_mm, (int, float))
            or not math.isfinite(minimum_gap_mm) or not 0 <= minimum_gap_mm <= 10000):
        raise ValueError("Minimum gap must be a finite nonnegative millimetre value at most 10000.")
    before = inspect_asset(asset_root, relative_path)
    if "sha256" not in before:
        raise ValueError("CAD file exceeds inspection size limit.")
    inspection = inspect_freecad(asset_root, relative_path, python_executable)
    after = inspect_asset(asset_root, relative_path)
    if after.get("sha256") != before["sha256"]:
        raise ValueError("CAD source changed during envelope inspection.")
    if inspection.get("objects_truncated"):
        raise ValueError("Document tree exceeds bounded inspection limit.")
    objects = {obj["name"]: obj for obj in inspection["objects"]}
    if any(name not in objects for name in object_names):
        raise ValueError("Selected object does not exist in the document tree.")
    selected = [{"name": name, "type": objects[name]["type"],
                 "parents": objects[name]["parents"],
                 "bounding_box_mm": objects[name]["shape"].get("bounding_box_mm")
                 if isinstance(objects[name].get("shape"), dict) else None}
                for name in object_names]
    pairs = []
    for index, first_name in enumerate(object_names):
        for second_name in object_names[index + 1:]:
            first = _bounds(objects[first_name].get("shape"))
            second = _bounds(objects[second_name].get("shape"))
            if first is None or second is None:
                pairs.append({"objects": [first_name, second_name], "status": "UNKNOWN",
                              "reason": "MISSING_OR_INVALID_ENVELOPE", "minimum_distance_lower_bound_mm": None})
                continue
            squared = sum(max(0, second[0][axis] - first[1][axis],
                              first[0][axis] - second[1][axis]) ** 2 for axis in range(3))
            lower_bound = math.sqrt(squared)
            pairs.append({"objects": [first_name, second_name],
                          "status": "LOWER_BOUND_EXCEEDS_THRESHOLD" if lower_bound > minimum_gap_mm
                          else "UNKNOWN",
                          "reason": "AABB_SEPARATED" if lower_bound > minimum_gap_mm
                          else "ENVELOPES_OVERLAP_OR_THRESHOLD_UNPROVEN",
                          "minimum_distance_lower_bound_mm": lower_bound})
    return {"path": before["path"], "source_sha256": before["sha256"],
            "units": "mm", "minimum_gap_mm": minimum_gap_mm, "objects": selected,
            "pairs": pairs, "note": "AABB separation is a conservative geometric lower bound. "
            "Overlapping boxes do not prove shape collision or physical fit."}
