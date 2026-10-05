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


def measure_distance(path, first_name, second_name):
    if not path.lower().endswith(".fcstd"):
        raise ValueError("Distance measurement requires FCStd.")
    document = FreeCAD.openDocument(path, True)
    try:
        first = document.getObject(first_name)
        second = document.getObject(second_name)
        if first is None or second is None or first == second:
            raise ValueError("Two distinct existing document objects are required.")
        if not hasattr(first, "Shape") or not hasattr(second, "Shape"):
            raise ValueError("Both objects must have shapes.")
        if first.Shape.isNull() or second.Shape.isNull():
            raise ValueError("Both shapes must be non-null.")
        distance, point_pairs, _ = first.Shape.distToShape(second.Shape)
        return {
            "format": "FCStd",
            "objects": [first_name, second_name],
            "minimum_distance_mm": distance,
            "closest_points_mm": [[_vector(first_point), _vector(second_point)]
                                  for first_point, second_point in point_pairs[:10]],
            "closest_points_truncated": len(point_pairs) > 10,
            "overlap_or_contact": distance == 0,
            "note": "Zero distance includes touching and overlap; it does not distinguish them.",
        }
    finally:
        FreeCAD.closeDocument(document.Name)


def _bounds(shape):
    bounds = shape.BoundBox
    return {"minimum": [bounds.XMin, bounds.YMin, bounds.ZMin],
            "maximum": [bounds.XMax, bounds.YMax, bounds.ZMax]}


def get_entities(path, entity, object_name, offset, limit):
    if path.lower().endswith((".step", ".stp")):
        shape = Part.read(path)
        document = None
    else:
        document = FreeCAD.openDocument(path, True)
        feature = document.getObject(object_name)
        if feature is None or not hasattr(feature, "Shape") or feature.Shape.isNull():
            FreeCAD.closeDocument(document.Name)
            raise ValueError("Expected an existing object with a non-null shape.")
        shape = feature.Shape
    try:
        items = getattr(shape, "Vertexes" if entity == "vertices" else entity.capitalize())
        records = []
        for index in range(offset, min(len(items), offset + limit)):
            item = items[index]
            record = {"index": index}
            if entity == "vertices":
                record["point_mm"] = _vector(item.Point)
            else:
                record["bounding_box_mm"] = _bounds(item)
                if entity == "edges":
                    record["length_mm"] = item.Length
                elif entity in {"faces", "shells"}:
                    record["area_mm2"] = item.Area
                elif entity == "solids":
                    record["volume_mm3"] = item.Volume if item.isValid() and item.isClosed() else None
            records.append(record)
        return {"format": "STEP" if document is None else "FCStd", "object": object_name or None,
                "entity": entity, "count": len(items), "offset": offset, "limit": limit,
                "has_more": offset + limit < len(items), "items": records}
    finally:
        if document is not None:
            FreeCAD.closeDocument(document.Name)


def _save_box(document, path, length, width, height):
    try:
        box = document.getObject("Box")
        if box is None or box.TypeId != "Part::Box" or len(document.Objects) != 1:
            raise ValueError("Expected one generated parametric Part::Box.")
        box.Length = float(length)
        box.Width = float(width)
        box.Height = float(height)
        document.recompute()
        if not box.Shape.isValid() or not box.Shape.isClosed() or len(box.Shape.Solids) != 1:
            raise ValueError("Generated shape is invalid.")
        document.saveAs(path)
    finally:
        FreeCAD.closeDocument(document.Name)
    reopened = FreeCAD.openDocument(path, True)
    try:
        saved_box = reopened.getObject("Box")
        if saved_box is None or not saved_box.Shape.isValid():
            raise ValueError("Saved document failed reopen validation.")
        return {"format": "FCStd", "object": "Box", "shape": _shape_summary(saved_box.Shape)}
    finally:
        FreeCAD.closeDocument(reopened.Name)


def create_box(path, length, width, height):
    document = FreeCAD.newDocument("DesignRevision")
    document.addObject("Part::Box", "Box")
    return _save_box(document, path, length, width, height)


def revise_box(path, source, length, width, height):
    if not source.lower().endswith(".fcstd"):
        raise ValueError("Expected an FCStd source revision.")
    return _save_box(FreeCAD.openDocument(source, True), path, length, width, height)


if __name__ == "__main__":
    operation = sys.argv[2] if len(sys.argv) > 2 else "inspect"
    if operation == "inspect" and len(sys.argv) == 3:
        result = inspect(sys.argv[1])
    elif operation == "distance" and len(sys.argv) == 5:
        result = measure_distance(sys.argv[1], sys.argv[3], sys.argv[4])
    elif operation == "entities" and len(sys.argv) == 7:
        result = get_entities(sys.argv[1], sys.argv[3], sys.argv[4],
                              int(sys.argv[5]), int(sys.argv[6]))
    elif operation == "create_box" and len(sys.argv) == 6:
        result = create_box(sys.argv[1], sys.argv[3], sys.argv[4], sys.argv[5])
    elif operation == "revise_box" and len(sys.argv) == 7:
        result = revise_box(sys.argv[1], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    else:
        raise ValueError("Unsupported worker operation or argument count.")
    print("DESIGN_MCP_RESULT=" + json.dumps(result, allow_nan=False))
