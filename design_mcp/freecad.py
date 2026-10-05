"""Bounded, read-only FreeCAD process adapter."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from design_mcp.catalog import MAX_BYTES, _inside, _root


def _run_worker(root: str | Path, relative_path: str, operation: str, *arguments: str,
                python_executable: str | Path | None = None) -> dict:
    base = _root(root)
    path = _inside(base, relative_path)
    if path.suffix.lower() not in {".fcstd", ".step", ".stp"} or not path.is_file():
        raise ValueError("Expected a regular FCStd or STEP file.")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("CAD file exceeds inspection size limit.")
    executable = Path(python_executable or os.environ.get("DESIGN_MCP_FREECAD_PYTHON", ""))
    if not executable.is_file() or executable.name.lower() not in {"python.exe", "python"}:
        raise RuntimeError("Configure DESIGN_MCP_FREECAD_PYTHON to FreeCAD's bundled Python.")
    worker = Path(__file__).with_name("freecad_worker.py")
    result = subprocess.run(
        [str(executable), "-I", str(worker), str(path), operation, *arguments],
        capture_output=True, text=True, timeout=60, env=os.environ.copy(), check=False,
    )
    prefix = "DESIGN_MCP_RESULT="
    payload = next((line[len(prefix):] for line in result.stdout.splitlines() if line.startswith(prefix)), None)
    if result.returncode != 0 or payload is None:
        raise RuntimeError(f"FreeCAD inspection failed (exit {result.returncode}): {result.stderr[-1000:]}")
    return {"path": path.relative_to(base).as_posix(), "units": {"length": "mm", "area": "mm2", "volume": "mm3"}, **json.loads(payload)}


def inspect_freecad(root: str | Path, relative_path: str, python_executable: str | Path | None = None) -> dict:
    return _run_worker(root, relative_path, "inspect", python_executable=python_executable)


def measure_freecad_distance(root: str | Path, relative_path: str, first_object: str,
                             second_object: str, python_executable: str | Path | None = None) -> dict:
    if not first_object or not second_object or first_object == second_object:
        raise ValueError("Specify two distinct document object names.")
    if len(first_object) > 128 or len(second_object) > 128:
        raise ValueError("Object names must be at most 128 characters.")
    if Path(relative_path).suffix.lower() != ".fcstd":
        raise ValueError("Distance measurement requires an FCStd document with two named objects.")
    return _run_worker(root, relative_path, "distance", first_object, second_object,
                       python_executable=python_executable)
