"""Runs inside FreeCAD's bundled Python, isolated from the MCP process."""

from __future__ import annotations

import json
import sys

import FreeCAD
import Part


def _vector(vector):
    return [vector.x, vector.y, vector.z]


def _shape_summary(shape):
    if shape.isNull():
        return None
    bounds = shape.BoundBox
    solids = len(shape.Solids)
    valid = shape.isValid()
    closed = shape.isClosed()
    return {
        "valid": valid,
        "closed": closed,
        "solids": solids,
        "shells": len(shape.Shells),
        "faces": len(shape.Faces),
        "edges": len(shape.Edges),
        "vertices": len(shape.Vertexes),
        "bounding_box_mm": {
            "minimum": [bounds.XMin, bounds.YMin, bounds.ZMin],
            "maximum": [bounds.XMax, bounds.YMax, bounds.ZMax],
            "extent": [bounds.XLength, bounds.YLength, bounds.ZLength],
        },
        "surface_area_mm2": shape.Area,
        "enclosed_volume_mm3": shape.Volume if valid and closed and solids else None,
        "volume_centroid_mm": _vector(shape.CenterOfMass) if valid and closed and solids and shape.Volume > 0 else None,
    }


def inspect(path):
    if path.lower().endswith((".step", ".stp")):
        shape = Part.read(path)
        return {"format": "STEP", "objects": [{"name": "ImportedShape", "type": "Part::Feature", "shape": _shape_summary(shape)}]}
    document = FreeCAD.openDocument(path, True)
    try:
        objects = []
        for obj in document.Objects[:200]:
            objects.append({
                "name": obj.Name,
                "label": obj.Label,
                "type": obj.TypeId,
                "parents": [parent.Name for parent in obj.InList if parent.Document == document][:50],
                "shape": _shape_summary(obj.Shape) if hasattr(obj, "Shape") else None,
            })
        return {"format": "FCStd", "object_count": len(document.Objects), "objects_truncated": len(document.Objects) > 200, "objects": objects}
    finally:
        FreeCAD.closeDocument(document.Name)


if __name__ == "__main__":
    print("DESIGN_MCP_RESULT=" + json.dumps(inspect(sys.argv[1]), allow_nan=False))
