from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path
from typing import Any

from design_mcp.catalog import MAX_BYTES, _inside, _root

MAX_MESH_TRIANGLES = 100_000


class MeshInspectionLimit(ValueError):
    pass


def _parse_stl(data: bytes) -> tuple[str, list[tuple[tuple[float, float, float], ...]]]:
    if len(data) >= 84:
        triangle_count = struct.unpack_from("<I", data, 80)[0]
        if len(data) == 84 + triangle_count * 50:
            if triangle_count > MAX_MESH_TRIANGLES:
                raise MeshInspectionLimit("Triangle inspection limit exceeded.")
            triangles = []
            for offset in range(84, len(data), 50):
                record = struct.unpack_from("<12f", data, offset)
                if not all(math.isfinite(value) for value in record):
                    raise ValueError("Non-finite STL record.")
                triangles.append((tuple(record[3:6]), tuple(record[6:9]), tuple(record[9:12])))
            return "binary", triangles

    try:
        lines = [line.strip() for line in data.decode("ascii").splitlines() if line.strip()]
    except UnicodeDecodeError as error:
        raise ValueError("Unrecognized STL encoding.") from error
    if not lines or not lines[0].lower().startswith("solid") or not lines[-1].lower().startswith("endsolid"):
        raise ValueError("Missing ASCII STL delimiters.")

    vertices = []
    facet_count = 0
    for line in lines:
        fields = line.split()
        if len(fields) >= 2 and fields[0].lower() == "facet" and fields[1].lower() == "normal":
            facet_count += 1
            if facet_count > MAX_MESH_TRIANGLES:
                raise MeshInspectionLimit("Triangle inspection limit exceeded.")
        if fields and fields[0].lower() == "vertex":
            if len(fields) != 4:
                raise ValueError("Invalid ASCII STL vertex.")
            try:
                vertex = tuple(float(value) for value in fields[1:])
            except ValueError as error:
                raise ValueError("Invalid ASCII STL vertex.") from error
            if not all(math.isfinite(value) for value in vertex):
                raise ValueError("Non-finite ASCII STL vertex.")
            vertices.append(vertex)
    if facet_count == 0 or len(vertices) != facet_count * 3:
        raise ValueError("Facet and vertex counts differ.")
    triangles = [tuple(vertices[index:index + 3]) for index in range(0, len(vertices), 3)]
    return "ascii", triangles


def _subtract(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return first[0] - second[0], first[1] - second[1], first[2] - second[2]


def _cross(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _dot(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return first[0] * second[0] + first[1] * second[1] + first[2] * second[2]


def _analyze(triangles: list[tuple[tuple[float, float, float], ...]]) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    vertex_indices: dict[tuple[float, float, float], int] = {}
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    face_entities = []
    surface_area = 0.0
    surface_centroid_sum = [0.0, 0.0, 0.0]

    for triangle in triangles:
        indices = []
        for vertex in triangle:
            index = vertex_indices.get(vertex)
            if index is None:
                index = len(vertices)
                vertex_indices[vertex] = index
                vertices.append(vertex)
            indices.append(index)
        face = (indices[0], indices[1], indices[2])
        faces.append(face)
        first, second, third = (vertices[index] for index in face)
        normal_raw = _cross(_subtract(second, first), _subtract(third, first))
        magnitude = math.sqrt(_dot(normal_raw, normal_raw))
        area = magnitude / 2.0
        surface_area += area
        for axis in range(3):
            surface_centroid_sum[axis] += area * (first[axis] + second[axis] + third[axis]) / 3.0
        normal = None if magnitude == 0 else [value / magnitude for value in normal_raw]
        face_entities.append({"vertices": list(face), "area_model_units2": area, "normal": normal})

    edges: dict[tuple[int, int], list[int]] = {}
    parents = list(range(len(faces)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for face_index, face in enumerate(faces):
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            key = (min(start, end), max(start, end))
            direction = 1 if start < end else -1
            entry = edges.get(key)
            if entry is None:
                edges[key] = [1, direction, face_index]
            else:
                entry[0] += 1
                entry[1] += direction
                first_root = root(entry[2])
                second_root = root(face_index)
                if first_root != second_root:
                    parents[second_root] = first_root

    boundary_edges = sum(1 for count, _, _ in edges.values() if count == 1)
    nonmanifold_edges = sum(1 for count, _, _ in edges.values() if count > 2)
    orientation_conflicts = sum(1 for count, direction, _ in edges.values() if count == 2 and direction != 0)
    closed = bool(edges) and boundary_edges == 0 and nonmanifold_edges == 0
    consistently_oriented = closed and orientation_conflicts == 0
    shell_count = len({root(index) for index in range(len(faces))}) if faces else 0

    edge_entities = [
        {"vertices": list(edge), "face_incidence": values[0]}
        for edge, values in sorted(edges.items())
    ]
    vertex_entities = [{"coordinates": list(vertex)} for vertex in vertices]

    if vertices:
        minimum = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
        maximum = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
        bounding_box = {
            "minimum": minimum,
            "maximum": maximum,
            "extent": [maximum[axis] - minimum[axis] for axis in range(3)],
        }
        reference = tuple((minimum[axis] + maximum[axis]) / 2.0 for axis in range(3))
    else:
        bounding_box = None
        reference = (0.0, 0.0, 0.0)

    volume_centroid = None
    volume = None
    if consistently_oriented:
        signed_volume = 0.0
        volume_centroid_sum = [0.0, 0.0, 0.0]
        for face in faces:
            first, second, third = (vertices[index] for index in face)
            relative_first = _subtract(first, reference)
            relative_second = _subtract(second, reference)
            relative_third = _subtract(third, reference)
            tetra_volume = _dot(relative_first, _cross(relative_second, relative_third)) / 6.0
            signed_volume += tetra_volume
            for axis in range(3):
                tetra_centroid = (reference[axis] + first[axis] + second[axis] + third[axis]) / 4.0
                volume_centroid_sum[axis] += tetra_volume * tetra_centroid
        if signed_volume != 0.0 and math.isfinite(signed_volume):
            volume = abs(signed_volume)
            volume_centroid = [value / signed_volume for value in volume_centroid_sum]

    surface_centroid = None
    if surface_area > 0:
        surface_centroid = [value / surface_area for value in surface_centroid_sum]

    metrics = {
        "coordinate_units": "UNKNOWN; STL does not encode units",
        "topology": {
            "face_count": len(faces),
            "unique_vertex_count": len(vertices),
            "unique_edge_count": len(edges),
            "edge_connected_shell_count": shell_count,
            "boundary_edge_count": boundary_edges,
            "nonmanifold_edge_count": nonmanifold_edges,
            "orientation_conflict_edge_count": orientation_conflicts,
            "closed_consistently_oriented": consistently_oriented,
            "self_intersections_checked": False,
        },
        "bounding_box_model_units": bounding_box,
        "surface_area_model_units2": surface_area,
        "surface_centroid_model_units": surface_centroid,
        "enclosed_volume_model_units3": volume,
        "volume_centroid_model_units": volume_centroid,
        "volume_status": (
            "CALCULATED_FROM_CLOSED_ORIENTED_TRIANGULATED_MESH"
            if volume is not None
            else "UNKNOWN_MESH_NOT_CLOSED_AND_CONSISTENTLY_ORIENTED"
        ),
    }
    entities = {"vertices": vertex_entities, "edges": edge_entities, "faces": face_entities}
    return metrics, entities


def _load_mesh(root: str | Path, relative_path: str) -> tuple[Path, bytes, str, list[tuple[tuple[float, float, float], ...]]]:
    base = _root(root)
    path = _inside(base, relative_path)
    if path.suffix.lower() != ".stl" or not path.is_file():
        raise ValueError("Expected an STL file beneath the configured root.")
    if path.stat().st_size > MAX_BYTES:
        raise MeshInspectionLimit("File inspection size limit exceeded.")
    data = path.read_bytes()
    encoding, triangles = _parse_stl(data)
    return path, data, encoding, triangles


def inspect_stl_geometry(root: str | Path, relative_path: str) -> dict[str, Any]:
    base = _root(root)
    path = _inside(base, relative_path)
    if path.suffix.lower() != ".stl" or not path.is_file():
        raise ValueError("Expected an STL file beneath the configured root.")
    size = path.stat().st_size
    if size > MAX_BYTES:
        return {"path": path.relative_to(base).as_posix(), "integrity": "UNKNOWN", "reason": "File inspection size limit exceeded."}
    data = path.read_bytes()
    result = {
        "path": path.relative_to(base).as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": size,
    }
    try:
        encoding, triangles = _parse_stl(data)
    except MeshInspectionLimit as error:
        return {**result, "integrity": "UNKNOWN", "reason": str(error)}
    except ValueError as error:
        return {**result, "integrity": "INVALID", "reason": str(error)}
    metrics, _ = _analyze(triangles)
    return {**result, "integrity": "STRUCTURE_VALID", "encoding": encoding, **metrics}


def get_stl_entities(
    root: str | Path,
    relative_path: str,
    entity: str = "faces",
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    if entity not in {"faces", "edges", "vertices"}:
        raise ValueError("entity must be faces, edges, or vertices.")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError("offset must be a non-negative integer.")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValueError("limit must be an integer from 1 to 500.")

    base = _root(root)
    path = _inside(base, relative_path)
    if path.suffix.lower() != ".stl" or not path.is_file():
        raise ValueError("Expected an STL file beneath the configured root.")
    if path.stat().st_size > MAX_BYTES:
        return {"path": path.relative_to(base).as_posix(), "integrity": "UNKNOWN", "entities": []}
    data = path.read_bytes()
    try:
        encoding, triangles = _parse_stl(data)
    except MeshInspectionLimit as error:
        return {"path": path.relative_to(base).as_posix(), "integrity": "UNKNOWN", "reason": str(error), "entities": []}
    except ValueError as error:
        return {"path": path.relative_to(base).as_posix(), "integrity": "INVALID", "reason": str(error), "entities": []}
    _, collections = _analyze(triangles)
    records = collections[entity]
    page = records[offset:offset + limit]
    return {
        "path": path.relative_to(base).as_posix(),
        "integrity": "STRUCTURE_VALID",
        "encoding": encoding,
        "coordinate_units": "UNKNOWN; STL does not encode units",
        "entity": entity,
        "entity_count": len(records),
        "offset": offset,
        "returned": len(page),
        "has_more": offset + len(page) < len(records),
        "entities": page,
    }
