from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path

IGNORED = {".git", ".venv", ".cache", "__pycache__", "node_modules"}
MAX_BYTES = 128 * 1024 * 1024


def _root(value: str | Path) -> Path:
    root = Path(value).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    return root


def _inside(root: Path, relative: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("Only relative paths inside the configured root are accepted.")
    path = root
    for part in raw.parts:
        if part not in ("", "."):
            path = path / part
            if path.is_symlink():
                raise ValueError("Symbolic links are not followed.")
    path = path.resolve(strict=True)
    if not path.is_relative_to(root):
        raise ValueError("Path escapes configured root.")
    return path


def list_assets(root: str | Path, relative_directory: str = ".") -> dict:
    base = _root(root)
    directory = _inside(base, relative_directory)
    if not directory.is_dir():
        raise NotADirectoryError(relative_directory)
    assets = []
    for current, folders, names in os.walk(directory, followlinks=False):
        folders[:] = [n for n in folders if n not in IGNORED and not (Path(current) / n).is_symlink()]
        for name in names:
            path = Path(current) / name
            if path.is_symlink() or not path.is_file():
                continue
            stat = path.stat()
            assets.append({"path": path.relative_to(base).as_posix(), "extension": path.suffix.lower(),
                           "size_bytes": stat.st_size,
                           "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()})
    assets.sort(key=lambda item: item["path"].casefold())
    return {"root_label": base.name, "asset_count": len(assets), "assets": assets}


def _stl(data: bytes) -> dict:
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if len(data) == 84 + count * 50:
            for offset in range(84, len(data), 50):
                if not all(math.isfinite(v) for v in struct.unpack_from("<12f", data, offset + 12)):
                    return {"integrity": "INVALID", "reason": "Non-finite vertex record."}
            return {"integrity": "STRUCTURE_VALID", "encoding": "binary", "triangle_records": count}
    try:
        lines = [line.strip() for line in data.decode("ascii").splitlines() if line.strip()]
    except UnicodeDecodeError:
        return {"integrity": "INVALID", "reason": "Unrecognized STL encoding."}
    if not lines or not lines[0].lower().startswith("solid") or not lines[-1].lower().startswith("endsolid"):
        return {"integrity": "INVALID", "reason": "Missing ASCII STL delimiters."}
    facets = sum(line.lower().startswith("facet normal ") for line in lines)
    vertices = 0
    for line in lines:
        if line.lower().startswith("vertex "):
            try:
                values = [float(v) for v in line.split()[1:]]
            except ValueError:
                return {"integrity": "INVALID", "reason": "Invalid vertex record."}
            if len(values) != 3 or not all(math.isfinite(v) for v in values):
                return {"integrity": "INVALID", "reason": "Invalid vertex record."}
            vertices += 1
    if vertices != 3 * facets:
        return {"integrity": "INVALID", "reason": "Facet and vertex counts differ."}
    return {"integrity": "STRUCTURE_VALID", "encoding": "ascii", "triangle_records": facets}


def inspect_asset(root: str | Path, relative_path: str) -> dict:
    base = _root(root)
    path = _inside(base, relative_path)
    if not path.is_file():
        raise ValueError("Expected a regular file.")
    size = path.stat().st_size
    result = {"path": path.relative_to(base).as_posix(), "extension": path.suffix.lower(), "size_bytes": size}
    if size > MAX_BYTES:
        return {**result, "integrity": "UNKNOWN", "reason": "Inspection size limit exceeded."}
    data = path.read_bytes()
    result["sha256"] = hashlib.sha256(data).hexdigest()
    ext = path.suffix.lower()
    if ext == ".stl":
        return {**result, **_stl(data)}
    if ext == ".gltf":
        try:
            document = json.loads(data)
            valid = document.get("asset", {}).get("version") == "2.0"
        except (UnicodeDecodeError, json.JSONDecodeError):
            valid = False
        return {**result, "integrity": "STRUCTURE_VALID" if valid else "INVALID",
                "external_resources_fetched": False}
    if ext == ".glb":
        valid = len(data) >= 12 and data[:4] == b"glTF"
        if valid:
            version, length = struct.unpack_from("<II", data, 4)
            valid = version == 2 and length == len(data)
        return {**result, "integrity": "STRUCTURE_VALID" if valid else "INVALID"}
    if ext in {".3mf", ".fcstd"}:
        required = "3D/3dmodel.model" if ext == ".3mf" else "Document.xml"
        try:
            with zipfile.ZipFile(path) as archive:
                expanded = sum(item.file_size for item in archive.infolist())
                valid = expanded <= 512 * 1024 * 1024 and required in archive.namelist() and archive.testzip() is None
        except (OSError, zipfile.BadZipFile, RuntimeError):
            valid = False
        return {**result, "integrity": "STRUCTURE_VALID" if valid else "INVALID"}
    return {**result, "integrity": "HASHED_ONLY", "reason": "Format is not parsed."}
