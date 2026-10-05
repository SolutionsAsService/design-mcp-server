"""Immutable generic project records with explicit, user-attested evidence links."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4

from design_mcp.cad_write import MAX_MANIFEST_BYTES, MAX_REVISION_ENTRIES, REVISION_ID, _output_root
from design_mcp.catalog import _inside, _root
from design_mcp.project_snapshot import _digest, _load_snapshot, inspect_project_snapshot

MAX_EVIDENCE = 20
STATUSES = {"VERIFIED", "MANUFACTURER", "MEASURED", "CALCULATED",
            "ESTIMATED", "ASSUMED", "UNKNOWN"}
UNITS = {"mm", "mm2", "mm3", "m", "g", "kg", "V", "A", "W", "Wh", "N"}


class EvidenceLink(TypedDict):
    evidence_id: str
    subject_kind: Literal["asset", "cad_revision"]
    subject_reference: str
    subject_sha256: str
    source_asset_path: str
    source_sha256: str
    claim: str
    evidence_status: str
    verification: str
    value: float | None
    unit: str | None


@dataclass(frozen=True)
class ProjectRecord:
    schema_version: int
    project_id: str
    name: str
    description: str
    snapshot_id: str
    snapshot_sha256: str
    created_utc: str
    evidence: list[EvidenceLink]
    parent_project_id: str | None = None
    parent_manifest_sha256: str | None = None


def _write_project(root: Path, record: ProjectRecord) -> dict:
    payload = asdict(record)
    payload["manifest_sha256"] = _digest(payload)
    path = root / f"project-{record.project_id}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True, allow_nan=False)
    return payload


def _load_project(root: Path, project_id: str) -> dict:
    if not isinstance(project_id, str) or not REVISION_ID.fullmatch(project_id):
        raise ValueError("Expected a 32-character lowercase hexadecimal project ID.")
    path = _inside(root, f"project-{project_id}.json")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Project record exceeds size limit.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    digest = payload.pop("manifest_sha256", None)
    if (payload.get("schema_version") != 1 or payload.get("project_id") != project_id
            or not isinstance(digest, str) or digest != _digest(payload)):
        raise ValueError("Project record failed identity or hash validation.")
    evidence = payload.get("evidence")
    if (not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE
            or not isinstance(payload.get("snapshot_id"), str)
            or not REVISION_ID.fullmatch(payload["snapshot_id"])
            or not isinstance(payload.get("snapshot_sha256"), str)
            or not isinstance(payload.get("name"), str)
            or not isinstance(payload.get("description"), str)
            or (payload.get("parent_project_id") is not None
                and (not isinstance(payload["parent_project_id"], str)
                     or not REVISION_ID.fullmatch(payload["parent_project_id"])))):
        raise ValueError("Project record has invalid structure.")
    for link in evidence:
        if (not isinstance(link, dict) or not isinstance(link.get("evidence_id"), str)
                or not REVISION_ID.fullmatch(link["evidence_id"])
                or link.get("subject_kind") not in {"asset", "cad_revision"}
                or not isinstance(link.get("subject_reference"), str)
                or not isinstance(link.get("source_asset_path"), str)
                or not isinstance(link.get("source_sha256"), str)
                or not isinstance(link.get("subject_sha256"), str)
                or link.get("evidence_status") not in STATUSES
                or link.get("verification") != "USER_ATTESTED_NOT_INDEPENDENTLY_CHECKED"
                or not isinstance(link.get("claim"), str)
                or (link.get("value") is None) != (link.get("unit") is None)
                or (link.get("value") is not None
                    and (isinstance(link["value"], bool)
                         or not isinstance(link["value"], (int, float))
                         or not math.isfinite(link["value"]) or link["unit"] not in UNITS))):
            raise ValueError("Project evidence has invalid structure.")
    return {**payload, "manifest_sha256": digest}


def _snapshot(asset_root: Path, revision_root: Path, snapshot_id: str) -> dict:
    record = _load_snapshot(revision_root, snapshot_id)
    inspection = inspect_project_snapshot(asset_root, revision_root, snapshot_id)
    if inspection["status"] != "CURRENT":
        raise ValueError("Project evidence requires a CURRENT snapshot; recheck or replace stale inputs.")
    return record


def create_project_record(asset_root: str | Path, revision_root: str | Path,
                          name: str, description: str, snapshot_id: str) -> dict:
    if (not isinstance(name, str) or not 1 <= len(name.strip()) <= 80
            or not isinstance(description, str) or len(description) > 500):
        raise ValueError("Project name must be 1–80 characters; description at most 500.")
    assets = _root(asset_root)
    root = _output_root(revision_root)
    if assets == root:
        raise ValueError("Asset and revision roots must be distinct.")
    source = _snapshot(assets, root, snapshot_id)
    record = ProjectRecord(1, uuid4().hex, name.strip(), description,
                           snapshot_id, source["manifest_sha256"],
                           datetime.now(timezone.utc).isoformat(), [])
    return _write_project(root, record)


def add_project_evidence(asset_root: str | Path, revision_root: str | Path,
                         project_id: str, subject_kind: str, subject_reference: str,
                         source_asset_path: str, claim: str, evidence_status: str,
                         value: float | None = None, unit: str | None = None) -> dict:
    assets = _root(asset_root)
    root = _output_root(revision_root)
    parent = _load_project(root, project_id)
    if len(parent["evidence"]) >= MAX_EVIDENCE:
        raise ValueError("Project record exceeds evidence limit.")
    snapshot = _snapshot(assets, root, parent["snapshot_id"])
    if snapshot["manifest_sha256"] != parent["snapshot_sha256"]:
        raise ValueError("Project snapshot manifest changed.")
    if (not isinstance(subject_kind, str) or subject_kind not in {"asset", "cad_revision"}
            or not isinstance(claim, str) or not 1 <= len(claim.strip()) <= 256
            or not isinstance(evidence_status, str) or evidence_status not in STATUSES):
        raise ValueError("Evidence requires a supported subject, short claim and status.")
    if ((value is None) != (unit is None)
            or (value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                       or not math.isfinite(value) or unit not in UNITS))):
        raise ValueError("Numeric evidence needs a finite value and supported explicit unit.")
    sources = {item["path"]: item["sha256"] for item in snapshot["assets"]}
    subjects = (sources if subject_kind == "asset" else
                {item["revision_id"]: item["model_sha256"] for item in snapshot["cad_revisions"]})
    if (not isinstance(source_asset_path, str) or source_asset_path not in sources
            or not isinstance(subject_reference, str) or subject_reference not in subjects):
        raise ValueError("Evidence source and subject must be references in the project snapshot.")
    link: EvidenceLink = {"evidence_id": uuid4().hex, "subject_kind": subject_kind,
                          "subject_reference": subject_reference,
                          "subject_sha256": subjects[subject_reference],
                          "source_asset_path": source_asset_path,
                          "source_sha256": sources[source_asset_path],
                          "claim": claim.strip(), "evidence_status": evidence_status,
                          "verification": "USER_ATTESTED_NOT_INDEPENDENTLY_CHECKED",
                          "value": float(value) if value is not None else None, "unit": unit}
    record = ProjectRecord(1, uuid4().hex, parent["name"], parent["description"],
                           parent["snapshot_id"], parent["snapshot_sha256"],
                           datetime.now(timezone.utc).isoformat(), parent["evidence"] + [link],
                           parent_project_id=project_id,
                           parent_manifest_sha256=parent["manifest_sha256"])
    return _write_project(root, record)


def inspect_project_record(asset_root: str | Path, revision_root: str | Path,
                           project_id: str) -> dict:
    assets = _root(asset_root)
    root = _output_root(revision_root)
    project = _load_project(root, project_id)
    parent_id = project.get("parent_project_id")
    if parent_id:
        parent = _load_project(root, parent_id)
        if parent["manifest_sha256"] != project.get("parent_manifest_sha256"):
            raise ValueError("Project parent manifest hash mismatch.")
    snapshot = _load_snapshot(root, project["snapshot_id"])
    if snapshot["manifest_sha256"] != project["snapshot_sha256"]:
        raise ValueError("Project snapshot manifest hash mismatch.")
    result = inspect_project_snapshot(assets, root, project["snapshot_id"])
    impacted = {(item["kind"], item.get("path", item.get("revision_id")))
                for item in result["changes"] + result["unknowns"]}
    relationships = []
    for link in project["evidence"]:
        source = ("asset", link["source_asset_path"])
        subject = (link["subject_kind"], link["subject_reference"])
        relationships.append({"evidence_id": link["evidence_id"], "source": source,
                              "subject": subject, "status": "RECHECK" if source in impacted
                              or subject in impacted else "CONTENT_UNCHANGED_NOT_VERIFIED"})
    return {"project": project, "snapshot_status": result["status"],
            "relationships": relationships, "changes": result["changes"],
            "unknowns": result["unknowns"]}


def list_project_records(revision_root: str | Path, offset: int = 0, limit: int = 10) -> dict:
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("Offset must be a nonnegative integer.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20.")
    root = _output_root(revision_root)
    identifiers = []
    for entry in root.iterdir():
        if entry.name.startswith("project-") and entry.suffix == ".json":
            identifier = entry.stem.removeprefix("project-")
            if REVISION_ID.fullmatch(identifier) and not entry.is_symlink() and entry.is_file():
                identifiers.append(identifier)
                if len(identifiers) > MAX_REVISION_ENTRIES:
                    raise ValueError("Project index exceeds entry limit.")
    identifiers.sort()
    page = []
    for identifier in identifiers[offset:offset + limit]:
        try:
            record = _load_project(root, identifier)
            page.append({"project_id": identifier, "status": "HASH_VERIFIED",
                         "name": record["name"], "snapshot_id": record["snapshot_id"],
                         "parent_project_id": record.get("parent_project_id"),
                         "evidence_count": len(record["evidence"])})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            page.append({"project_id": identifier, "status": "INVALID"})
    return {"total": len(identifiers), "offset": offset, "limit": limit,
            "has_more": offset + limit < len(identifiers), "projects": page}
