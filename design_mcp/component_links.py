"""Immutable candidate and assembly handoffs for externally obtained MCP observations."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from design_mcp.cad_write import MAX_MANIFEST_BYTES, MAX_REVISION_ENTRIES, REVISION_ID, _output_root
from design_mcp.catalog import _inside
from design_mcp.project_snapshot import _digest

MAX_PACKET_BYTES = 32 * 1024
MAX_INSTANCES = 20
PART_CODE = re.compile(r"C[0-9]{1,10}\Z")


def _write_record(root: Path, prefix: str, record: dict) -> dict:
    record["manifest_sha256"] = _digest(record)
    if len(json.dumps(record, sort_keys=True, allow_nan=False).encode("utf-8")) > MAX_MANIFEST_BYTES:
        raise ValueError("Record exceeds size limit.")
    path = root / f"{prefix}-{record[f'{prefix}_id']}.json"
    with path.open("x", encoding="utf-8") as output:
        json.dump(record, output, sort_keys=True, allow_nan=False)
    return record


def _load_record(root: Path, prefix: str, identifier: str) -> dict:
    if not isinstance(identifier, str) or not REVISION_ID.fullmatch(identifier):
        raise ValueError("Expected a 32-character lowercase hexadecimal record ID.")
    path = _inside(root, f"{prefix}-{identifier}.json")
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Record exceeds size limit.")
    record = json.loads(path.read_text(encoding="utf-8"))
    digest = record.pop("manifest_sha256", None)
    if (record.get("schema_version") != 1 or record.get(f"{prefix}_id") != identifier
            or not isinstance(digest, str) or digest != _digest(record)):
        raise ValueError("Record failed identity or hash validation.")
    return {**record, "manifest_sha256": digest}


def register_component_candidate(revision_root: str | Path,
                                 part_output: dict, footprint_output: dict) -> dict:
    """Store caller-forwarded pcbparts and KiCad outputs; never certify the pairing."""
    if not isinstance(part_output, dict) or not isinstance(footprint_output, dict):
        raise ValueError("Expected two structured provider outputs.")
    if (len(json.dumps(part_output, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_PACKET_BYTES
            or len(json.dumps(footprint_output, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_PACKET_BYTES):
        raise ValueError("Provider output exceeds size limit.")
    part_code = part_output.get("lcsc")
    manufacturer = part_output.get("manufacturer")
    part_number = part_output.get("model")
    library = footprint_output.get("library")
    footprint = footprint_output.get("name")
    full_name = footprint_output.get("full_name")
    pad_count = footprint_output.get("pad_count")
    if (not isinstance(part_code, str) or not PART_CODE.fullmatch(part_code)
            or not isinstance(manufacturer, str) or not 1 <= len(manufacturer) <= 128
            or not isinstance(part_number, str) or not 1 <= len(part_number) <= 128
            or not isinstance(library, str) or not 1 <= len(library) <= 128
            or not isinstance(footprint, str) or not 1 <= len(footprint) <= 128
            or full_name != f"{library}:{footprint}"
            or isinstance(pad_count, bool) or not isinstance(pad_count, int)
            or not 1 <= pad_count <= 2000):
        raise ValueError("Provider outputs are missing required catalog or footprint identifiers.")
    record = {"schema_version": 1, "candidate_id": uuid4().hex,
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "part_provider": "pcbparts.jlc_get_part",
              "footprint_provider": "kicad.library_search",
              "part_output": part_output, "footprint_output": footprint_output,
              "part": {"manufacturer": manufacturer, "mpn": part_number, "lcsc": part_code},
              "footprint": {"library_id": full_name, "pad_count": pad_count},
              "envelope_status": "UNKNOWN_NO_SOURCE_BACKED_DIMENSIONS",
              "pairing_status": "UNVERIFIED_CANDIDATE_NOT_PIN_OR_PACKAGE_CHECKED",
              "provenance": "CALLER_FORWARDED_PROVIDER_OUTPUT_NOT_AUTHENTICATED"}
    return _write_record(_output_root(revision_root), "candidate", record)


def inspect_component_candidate(revision_root: str | Path, candidate_id: str) -> dict:
    record = _load_record(_output_root(revision_root), "candidate", candidate_id)
    if (record.get("part", {}).get("lcsc") != record.get("part_output", {}).get("lcsc")
            or record.get("part", {}).get("mpn") != record.get("part_output", {}).get("model")
            or record.get("part", {}).get("manufacturer") != record.get("part_output", {}).get("manufacturer")
            or record.get("footprint", {}).get("library_id") !=
            record.get("footprint_output", {}).get("full_name")
            or record.get("footprint", {}).get("pad_count") !=
            record.get("footprint_output", {}).get("pad_count")):
        raise ValueError("Candidate normalization does not match stored provider output.")
    return {"candidate": record, "geometry_status": "UNKNOWN",
            "compatibility_status": "UNKNOWN", "note": "Neither dimensions nor pin mapping were verified."}


def _validate_instances(instances: list[dict]) -> None:
    if not isinstance(instances, list) or not 1 <= len(instances) <= MAX_INSTANCES:
        raise ValueError("Assembly requires 1–20 instances.")
    references = set()
    for instance in instances:
        if not isinstance(instance, dict):
            raise ValueError("Assembly instances must be structured objects.")
        reference = instance.get("reference")
        position = instance.get("position_mm")
        if (not isinstance(reference, str) or not 1 <= len(reference) <= 64
                or reference in references or not isinstance(instance.get("candidate_id"), str)
                or not isinstance(position, list) or len(position) != 3
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) or abs(value) > 10000 for value in position)):
            raise ValueError("Instance needs a unique reference, candidate ID and finite mm position.")
        references.add(reference)
    parent_by_ref = {item["reference"]: item.get("parent_reference") for item in instances}
    for reference, parent in parent_by_ref.items():
        if parent is not None and (not isinstance(parent, str) or parent not in references
                                   or parent == reference):
            raise ValueError("Instance parent must reference another assembly instance.")
        visited = {reference}
        while parent is not None:
            if parent in visited:
                raise ValueError("Assembly hierarchy contains a cycle.")
            visited.add(parent)
            parent = parent_by_ref[parent]


def create_assembly_manifest(revision_root: str | Path, name: str,
                             instances: list[dict]) -> dict:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ValueError("Assembly name must contain 1–80 characters.")
    _validate_instances(instances)
    root = _output_root(revision_root)
    normalized = []
    for instance in instances:
        candidate = inspect_component_candidate(root, instance["candidate_id"])["candidate"]
        normalized.append({"reference": instance["reference"],
                           "parent_reference": instance.get("parent_reference"),
                           "candidate_id": instance["candidate_id"],
                           "candidate_sha256": candidate["manifest_sha256"],
                           "position_mm": [float(value) for value in instance["position_mm"]]})
    record = {"schema_version": 1, "assembly_id": uuid4().hex,
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "name": name.strip(), "instances": normalized,
              "status": "HIERARCHY_ONLY_UNVERIFIED_COMPONENTS"}
    return _write_record(root, "assembly", record)


def inspect_assembly_manifest(revision_root: str | Path, assembly_id: str) -> dict:
    root = _output_root(revision_root)
    record = _load_record(root, "assembly", assembly_id)
    _validate_instances(record["instances"])
    stale = []
    unknowns = []
    for instance in record["instances"]:
        try:
            candidate = inspect_component_candidate(root, instance["candidate_id"])["candidate"]
            if candidate["manifest_sha256"] != instance["candidate_sha256"]:
                stale.append(instance["reference"])
        except FileNotFoundError:
            stale.append(instance["reference"])
        except (ValueError, OSError, KeyError, TypeError):
            unknowns.append(instance["reference"])
    return {"assembly": record, "reference_status": "STALE" if stale else
            ("UNKNOWN" if unknowns else "HASHES_CURRENT"),
            "stale_instances": stale, "unknown_instances": unknowns,
            "fit_status": "UNKNOWN_MISSING_SOURCE_BACKED_ENVELOPES",
            "note": "Positions are caller-supplied. No physical instances, constraints or fit are validated."}


def list_component_candidates(revision_root: str | Path, offset: int = 0,
                              limit: int = 10) -> dict:
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("Offset must be a nonnegative integer.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20.")
    root = _output_root(revision_root)
    identifiers = []
    for entry in root.iterdir():
        if entry.name.startswith("candidate-") and entry.suffix == ".json":
            identifier = entry.stem.removeprefix("candidate-")
            if REVISION_ID.fullmatch(identifier) and not entry.is_symlink() and entry.is_file():
                identifiers.append(identifier)
                if len(identifiers) > MAX_REVISION_ENTRIES:
                    raise ValueError("Candidate index exceeds entry limit.")
    identifiers.sort()
    page = []
    for identifier in identifiers[offset:offset + limit]:
        try:
            record = inspect_component_candidate(root, identifier)["candidate"]
            page.append({"candidate_id": identifier, "status": "HASH_VERIFIED_NOT_COMPATIBILITY_VERIFIED",
                         "part": record["part"], "footprint": record["footprint"]})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            page.append({"candidate_id": identifier, "status": "INVALID"})
    return {"total": len(identifiers), "offset": offset, "limit": limit,
            "has_more": offset + limit < len(identifiers), "candidates": page}


def list_assembly_manifests(revision_root: str | Path, offset: int = 0,
                            limit: int = 10) -> dict:
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("Offset must be a nonnegative integer.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20.")
    root = _output_root(revision_root)
    identifiers = []
    for entry in root.iterdir():
        if entry.name.startswith("assembly-") and entry.suffix == ".json":
            identifier = entry.stem.removeprefix("assembly-")
            if REVISION_ID.fullmatch(identifier) and not entry.is_symlink() and entry.is_file():
                identifiers.append(identifier)
                if len(identifiers) > MAX_REVISION_ENTRIES:
                    raise ValueError("Assembly index exceeds entry limit.")
    identifiers.sort()
    page = []
    for identifier in identifiers[offset:offset + limit]:
        try:
            record = _load_record(root, "assembly", identifier)
            _validate_instances(record["instances"])
            page.append({"assembly_id": identifier, "status": "HASH_VERIFIED_NOT_FIT_VALIDATED",
                         "name": record["name"], "instance_count": len(record["instances"])})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            page.append({"assembly_id": identifier, "status": "INVALID"})
    return {"total": len(identifiers), "offset": offset, "limit": limit,
            "has_more": offset + limit < len(identifiers), "assemblies": page}
