"""Runs inside FreeCAD's bundled Python, isolated from the MCP process."""

from __future__ import annotations

import json
import math
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
    volume = shape.Volume if valid and closed and solids else None
    centroid = None
    if volume is not None and volume > 0:
        solid_parts = [(solid.Volume, solid.CenterOfMass) for solid in shape.Solids
                       if solid.isValid() and solid.isClosed() and solid.Volume > 0]
        total = sum(part_volume for part_volume, _ in solid_parts)
        if total > 0 and math.isclose(total, volume, rel_tol=1e-7, abs_tol=1e-7):
            centroid = [sum(part_volume * getattr(center, axis) for part_volume, center in solid_parts) / total
                        for axis in ("x", "y", "z")]
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
        "enclosed_volume_mm3": volume,
        "volume_centroid_mm": centroid,
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
        intersection_volume = None
        relationship = "SEPARATED" if distance > 1e-7 else "UNKNOWN_ZERO_DISTANCE_NON_SOLID"
        if distance <= 1e-7 and all(shape.isValid() and shape.isClosed() and shape.Solids
                                    for shape in (first.Shape, second.Shape)):
            try:
                common = first.Shape.common(second.Shape)
                if common.isValid():
                    intersection_volume = common.Volume
                    relationship = ("VOLUMETRIC_OVERLAP" if intersection_volume > 1e-6
                                    else "ZERO_DISTANCE_NO_VOLUME_OVERLAP")
                else:
                    relationship = "UNKNOWN_BOOLEAN_INVALID"
            except Exception:
                relationship = "UNKNOWN_BOOLEAN_FAILED"
        return {
            "format": "FCStd",
            "objects": [first_name, second_name],
            "minimum_distance_mm": distance,
            "closest_points_mm": [[_vector(first_point), _vector(second_point)]
                                  for first_point, second_point in point_pairs[:10]],
            "closest_points_truncated": len(point_pairs) > 10,
            "overlap_or_contact": distance <= 1e-7,
            "relationship": relationship,
            "intersection_volume_mm3": intersection_volume,
            "overlap_threshold_mm3": 1e-6,
            "note": "Zero distance without measurable volume overlap may mean contact or numerical coincidence; non-solids are not classified volumetrically.",
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


def export_wireframe(path, object_name, output_path):
    document = FreeCAD.openDocument(path, True)
    try:
        feature = document.getObject(object_name)
        if feature is None or feature.TypeId != "Part::Box" or len(document.Objects) != 1:
            raise ValueError("Expected one generated parametric box.")
        shape = feature.Shape
        if not shape.isValid() or shape.isNull():
            raise ValueError("Expected a valid shape.")
        extent = max(shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength)
        points, triangles = shape.tessellate(max(extent / 100, 0.1))
        if not 0 < len(triangles) <= 5000 or len(points) > 10000:
            raise ValueError("Tessellation exceeds preview limits or is empty.")
        projected = [(0.70710678 * (point.x - point.y),
                      0.40824829 * (point.x + point.y) - 0.81649658 * point.z)
                     for point in points]
        if not all(math.isfinite(coordinate) for pair in projected for coordinate in pair):
            raise ValueError("Preview contains non-finite coordinates.")
        minimum_x = min(pair[0] for pair in projected)
        minimum_y = min(pair[1] for pair in projected)
        span_x = max(pair[0] for pair in projected) - minimum_x
        span_y = max(pair[1] for pair in projected) - minimum_y
        scale = min(560 / max(span_x, 1e-9), 400 / max(span_y, 1e-9))
        coordinates = [(320 + (x - minimum_x - span_x / 2) * scale,
                        240 - (y - minimum_y - span_y / 2) * scale)
                       for x, y in projected]
        edges = set()
        for triangle in triangles:
            for first, second in ((triangle[0], triangle[1]),
                                  (triangle[1], triangle[2]),
                                  (triangle[2], triangle[0])):
                if first == second or not 0 <= first < len(points) or not 0 <= second < len(points):
                    raise ValueError("Invalid tessellation edge.")
                edges.add(tuple(sorted((first, second))))
        segments = []
        for first, second in sorted(edges):
            x1, y1 = coordinates[first]
            x2, y2 = coordinates[second]
            segments.append(f"M{x1:.2f},{y1:.2f}L{x2:.2f},{y2:.2f}")
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" '
               'viewBox="0 0 640 480"><rect width="640" height="480" fill="#fff"/>'
               '<path fill="none" stroke="#243b53" stroke-width="1" d="'
               + " ".join(segments) + '"/></svg>')
        with open(output_path, "x", encoding="utf-8") as output:
            output.write(svg)
        return {"triangle_count": len(triangles), "vertex_count": len(points),
                "wireframe_edge_count": len(edges), "canvas_px": [640, 480]}
    finally:
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
    elif operation == "preview" and len(sys.argv) == 5:
        result = export_wireframe(sys.argv[1], sys.argv[3], sys.argv[4])
    elif operation == "create_box" and len(sys.argv) == 6:
        result = create_box(sys.argv[1], sys.argv[3], sys.argv[4], sys.argv[5])
    elif operation == "revise_box" and len(sys.argv) == 7:
        result = revise_box(sys.argv[1], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    else:
        raise ValueError("Unsupported worker operation or argument count.")
    print("DESIGN_MCP_RESULT=" + json.dumps(result, allow_nan=False))
