"""Opt-in, copy-on-write FreeCAD revisions for generic geometry."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4

from design_mcp.catalog import MAX_BYTES, _inside, _root
from design_mcp.freecad import inspect_freecad

REVISION_ID = re.compile(r"[0-9a-f]{32}\Z")


def _output_root(value: str | Path) -> Path:
    raw = Path(value)
    if raw.is_symlink():
        raise ValueError("Output root must not be a symbolic link.")
    return _root(raw)


def _runtime(executable: str | Path | None) -> Path:
    candidate = Path(executable or os.environ.get("DESIGN_MCP_FREECAD_PYTHON", ""))
    if not candidate.is_file() or candidate.name.lower() not in {"python.exe", "python"}:
        raise RuntimeError("Configure DESIGN_MCP_FREECAD_PYTHON to FreeCAD's bundled Python.")
    return candidate


def create_box_revision(output_root: str | Path, length_mm: float, width_mm: float,
                        height_mm: float, python_executable: str | Path | None = None) -> dict:
    dimensions = (length_mm, width_mm, height_mm)
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or not 0 < value <= 10000 for value in dimensions):
        raise ValueError("All dimensions must be finite positive millimetres, at most 10000.")
    root = _output_root(output_root)
    executable = _runtime(python_executable)
    revision_id = uuid4().hex
    name = f"revision-{revision_id}"
    model = root / f"{name}.fcstd"
    manifest_path = root / f"{name}.json"
    if model.exists() or manifest_path.exists():
        raise FileExistsError("Revision ID already exists.")
    worker = Path(__file__).with_name("freecad_worker.py")
    try:
        result = subprocess.run(
            [str(executable), "-I", str(worker), str(model), "create_box",
             *(str(value) for value in dimensions)],
            capture_output=True, text=True, timeout=60, env=os.environ.copy(), check=False,
        )
        prefix = "DESIGN_MCP_RESULT="
        payload = next((line[len(prefix):] for line in result.stdout.splitlines()
                        if line.startswith(prefix)), None)
        if result.returncode != 0 or payload is None:
            raise RuntimeError(f"FreeCAD creation failed (exit {result.returncode}): {result.stderr[-1000:]}")
        geometry = json.loads(payload)
        shape = geometry.get("shape") or {}
        extents = shape.get("bounding_box_mm", {}).get("extent", [])
        if (model.is_symlink() or not model.is_file() or model.stat().st_size > MAX_BYTES
                or shape.get("valid") is not True
                or shape.get("closed") is not True or shape.get("solids") != 1
                or len(extents) != 3
                or any(not isinstance(actual, (int, float)) or not math.isfinite(actual)
                       or not math.isclose(actual, requested, rel_tol=1e-7, abs_tol=1e-6)
                       for actual, requested in zip(extents, dimensions))):
            raise RuntimeError("FreeCAD output was missing, oversized or geometrically invalid.")
        digest = hashlib.sha256(model.read_bytes()).hexdigest()
        record = {
            "revision_id": revision_id,
            "model": model.name,
            "sha256": digest,
            "operation": "create_box",
            "dimensions_mm": dict(zip(("length", "width", "height"), dimensions)),
            "validation": "REOPENED_GEOMETRY_ONLY",
            "geometry": geometry,
        }
        temporary_manifest = root / f"{name}.json.tmp"
        with temporary_manifest.open("x", encoding="utf-8") as output:
            json.dump(record, output, sort_keys=True)
        os.replace(temporary_manifest, manifest_path)
        return record
    except Exception:
        model.unlink(missing_ok=True)
        (root / f"{name}.json.tmp").unlink(missing_ok=True)
        raise


def inspect_revision(output_root: str | Path, revision_id: str,
                     python_executable: str | Path | None = None) -> dict:
    if not REVISION_ID.fullmatch(revision_id):
        raise ValueError("Expected a 32-character lowercase hexadecimal revision ID.")
    root = _output_root(output_root)
    name = f"revision-{revision_id}"
    manifest = _inside(root, f"{name}.json")
    model = _inside(root, f"{name}.fcstd")
    record = json.loads(manifest.read_text(encoding="utf-8"))
    if record.get("revision_id") != revision_id or record.get("model") != model.name:
        raise ValueError("Revision manifest does not match model path.")
    if (model.stat().st_size > MAX_BYTES
            or hashlib.sha256(model.read_bytes()).hexdigest() != record.get("sha256")):
        raise ValueError("Revision model failed hash or size validation.")
    return {"revision": record, "inspection": inspect_freecad(root, model.name, python_executable)}
