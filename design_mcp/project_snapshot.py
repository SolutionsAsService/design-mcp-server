"""Bounded, hash-linked snapshots of generic assets and CAD revisions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from design_mcp.cad_write import (MAX_MANIFEST_BYTES, MAX_REVISION_ENTRIES,
                                  REVISION_ID, _load_revision, _output_root)
from design_mcp.catalog import MAX_BYTES, _inside, _root, inspect_asset

MAX_REFERENCES = 20


def _digest(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True).encode("utf-8")).hexdigest()


def _snapshot_path(root: Path, snapshot_id: str) -> Path:
    if not REVISION_ID.fullmatch(snapshot_id):
        raise ValueError("Expected a 32-character lowercase hexadecimal snapshot ID.")
    return _inside(root, f"snapshot-{snapshot_id}.json")


def _load_snapshot(root: Path, snapshot_id: str) -> dict:
    path = _snapshot_path(root, snapshot_id)
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Snapshot exceeds size limit.")
    record = json.loads(path.read_text(encoding="utf-8"))
    digest = record.pop("manifest_sha256", None)
    if (record.get("snapshot_id") != snapshot_id or record.get("schema_version") != 1
            or not isinstance(digest, str) or digest != _digest(record)):
        raise ValueError("Snapshot manifest failed identity or hash validation.")
    assets, revisions = record.get("assets"), record.get("cad_revisions")
    if (not isinstance(assets, list) or not isinstance(revisions, list)
            or not 1 <= len(assets) + len(revisions) <= MAX_REFERENCES
            or any(not isinstance(item, dict) or not isinstance(item.get("path"), str)
                   or not isinstance(item.get("sha256"), str)
                   or not isinstance(item.get("size_bytes"), int) for item in assets)
            or any(not isinstance(item, dict) or not isinstance(item.get("revision_id"), str)
                   or not REVISION_ID.fullmatch(item["revision_id"])
                   or not isinstance(item.get("model_sha256"), str) for item in revisions)):
        raise ValueError("Snapshot manifest has invalid reference structure.")
    return {**record, "manifest_sha256": digest}


def create_project_snapshot(asset_root: str | Path, revision_root: str | Path,
                            name: str, asset_paths: list[str], revision_ids: list[str]) -> dict:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ValueError("Snapshot name must contain 1–80 characters.")
    if (not isinstance(asset_paths, list) or not isinstance(revision_ids, list)
            or not 1 <= len(asset_paths) + len(revision_ids) <= MAX_REFERENCES):
        raise ValueError("Provide 1–20 asset and/or CAD revision references.")
    assets_root = _root(asset_root)
    revisions_root = _output_root(revision_root)
    if assets_root == revisions_root:
        raise ValueError("Asset and revision roots must be distinct.")
    assets = []
    seen_assets = set()
    for relative_path in asset_paths:
        if not isinstance(relative_path, str):
            raise ValueError("Asset paths must be strings.")
        result = inspect_asset(assets_root, relative_path)
        path = result["path"]
        if path in seen_assets or "sha256" not in result:
            raise ValueError("Duplicate or oversized asset cannot be snapshotted.")
        seen_assets.add(path)
        assets.append({"path": path, "sha256": result["sha256"],
                       "size_bytes": result["size_bytes"]})
    revisions = []
    seen_revisions = set()
    for revision_id in revision_ids:
        if not isinstance(revision_id, str) or revision_id in seen_revisions:
            raise ValueError("Revision IDs must be unique strings.")
        record, _ = _load_revision(revisions_root, revision_id)
        seen_revisions.add(revision_id)
        revisions.append({"revision_id": revision_id, "model_sha256": record["sha256"]})
    record = {"schema_version": 1, "snapshot_id": uuid4().hex, "name": name.strip(),
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "assets": assets, "cad_revisions": revisions}
    record["manifest_sha256"] = _digest(record)
    output = revisions_root / f"snapshot-{record['snapshot_id']}.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, sort_keys=True)
    return record


def inspect_project_snapshot(asset_root: str | Path, revision_root: str | Path,
                             snapshot_id: str) -> dict:
    assets_root = _root(asset_root)
    revisions_root = _output_root(revision_root)
    record = _load_snapshot(revisions_root, snapshot_id)
    changes = []
    unknowns = []
    for asset in record["assets"]:
        try:
            result = inspect_asset(assets_root, asset["path"])
            if "sha256" not in result:
                unknowns.append({"kind": "asset", "path": asset["path"], "reason": "SIZE_LIMIT"})
            elif (result["sha256"] != asset["sha256"]
                  or result["size_bytes"] != asset["size_bytes"]):
                changes.append({"kind": "asset", "path": asset["path"], "status": "CHANGED"})
        except FileNotFoundError:
            changes.append({"kind": "asset", "path": asset["path"], "status": "MISSING"})
        except (OSError, ValueError) as exc:
            unknowns.append({"kind": "asset", "path": asset["path"], "reason": type(exc).__name__})
    for revision in record["cad_revisions"]:
        try:
            model = _inside(revisions_root, f"revision-{revision['revision_id']}.fcstd")
            if model.stat().st_size > MAX_BYTES:
                unknowns.append({"kind": "cad_revision", "revision_id": revision["revision_id"],
                                 "reason": "SIZE_LIMIT"})
                continue
            if hashlib.sha256(model.read_bytes()).hexdigest() != revision["model_sha256"]:
                changes.append({"kind": "cad_revision", "revision_id": revision["revision_id"],
                                "status": "CHANGED"})
                continue
            actual, _ = _load_revision(revisions_root, revision["revision_id"])
            if actual["sha256"] != revision["model_sha256"]:
                changes.append({"kind": "cad_revision", "revision_id": revision["revision_id"],
                                "status": "CHANGED"})
        except FileNotFoundError:
            changes.append({"kind": "cad_revision", "revision_id": revision["revision_id"],
                            "status": "MISSING"})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            unknowns.append({"kind": "cad_revision", "revision_id": revision["revision_id"],
                             "reason": type(exc).__name__})
    status = "STALE" if changes else ("UNKNOWN" if unknowns else "CURRENT")
    return {"snapshot": record, "status": status, "changes": changes, "unknowns": unknowns,
            "recheck": sorted({"ASSET_INSPECTION" if item["kind"] == "asset" else "CAD_INSPECTION"
                               for item in changes + unknowns})}


def list_project_snapshots(revision_root: str | Path, offset: int = 0, limit: int = 10) -> dict:
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("Offset must be a nonnegative integer.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20.")
    root = _output_root(revision_root)
    identifiers = []
    for entry in root.iterdir():
        if entry.name.startswith("snapshot-") and entry.suffix == ".json":
            identifier = entry.stem.removeprefix("snapshot-")
            if REVISION_ID.fullmatch(identifier) and not entry.is_symlink() and entry.is_file():
                identifiers.append(identifier)
                if len(identifiers) > MAX_REVISION_ENTRIES:
                    raise ValueError("Snapshot index exceeds entry limit.")
    identifiers.sort()
    page = []
    for identifier in identifiers[offset:offset + limit]:
        try:
            record = _load_snapshot(root, identifier)
            page.append({"snapshot_id": identifier, "status": "HASH_VERIFIED",
                         "name": record["name"], "created_utc": record["created_utc"],
                         "asset_count": len(record["assets"]),
                         "cad_revision_count": len(record["cad_revisions"])})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            page.append({"snapshot_id": identifier, "status": "INVALID"})
    return {"total": len(identifiers), "offset": offset, "limit": limit,
            "has_more": offset + limit < len(identifiers), "snapshots": page}
