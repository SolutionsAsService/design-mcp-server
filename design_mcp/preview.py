"""Hash-linked, bounded wireframe previews of generated CAD revisions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

from design_mcp.cad_write import _load_revision, _output_root, _runtime
from design_mcp.catalog import _inside

MAX_PREVIEW_BYTES = 2 * 1024 * 1024
PREVIEW_ID = re.compile(r"[0-9a-f]{32}\Z")


def preview_cad_revision(revision_root: str | Path, preview_root: str | Path,
                         revision_id: str, python_executable: str | Path | None = None) -> dict:
    source_root = _output_root(revision_root)
    destination_root = _output_root(preview_root)
    if source_root == destination_root:
        raise ValueError("Preview root must be separate from the revision root.")
    revision, source = _load_revision(source_root, revision_id)
    if revision.get("operation") not in {"create_box", "revise_box", "rollback_box"}:
        raise ValueError("Preview requires a generated box revision.")
    executable = _runtime(python_executable)
    preview_id = uuid4().hex
    name = f"preview-{preview_id}"
    svg_path = destination_root / f"{name}.svg"
    manifest_path = destination_root / f"{name}.json"
    temporary_manifest = destination_root / f"{name}.json.tmp"
    if svg_path.exists() or manifest_path.exists():
        raise FileExistsError("Preview ID already exists.")
    worker = Path(__file__).with_name("freecad_worker.py")
    try:
        result = subprocess.run(
            [str(executable), "-I", str(worker), str(source), "preview", "Box", str(svg_path)],
            capture_output=True, text=True, timeout=60, env=os.environ.copy(), check=False,
        )
        prefix = "DESIGN_MCP_RESULT="
        payload = next((line[len(prefix):] for line in result.stdout.splitlines()
                        if line.startswith(prefix)), None)
        if result.returncode != 0 or payload is None:
            raise RuntimeError(f"FreeCAD preview failed (exit {result.returncode}): {result.stderr[-1000:]}")
        if hashlib.sha256(source.read_bytes()).hexdigest() != revision["sha256"]:
            raise RuntimeError("Source revision changed during preview; result discarded.")
        details = json.loads(payload)
        if (svg_path.is_symlink() or not svg_path.is_file()
                or not 0 < svg_path.stat().st_size <= MAX_PREVIEW_BYTES
                or details.get("triangle_count", 0) <= 0):
            raise RuntimeError("Preview is missing, oversized or empty.")
        svg = svg_path.read_bytes()
        try:
            valid_svg = ET.fromstring(svg).tag == "{http://www.w3.org/2000/svg}svg"
        except ET.ParseError:
            valid_svg = False
        if not valid_svg:
            raise RuntimeError("Preview is not a valid SVG document.")
        record = {"preview_id": preview_id, "revision_id": revision_id,
                  "source_sha256": revision["sha256"], "svg": svg_path.name,
                  "svg_sha256": hashlib.sha256(svg).hexdigest(), "kind": "ISOMETRIC_WIREFRAME",
                  "validation": "SOURCE_HASH_AND_SVG_STRUCTURE_ONLY", "geometry": details}
        with temporary_manifest.open("x", encoding="utf-8") as output:
            json.dump(record, output, sort_keys=True)
        os.replace(temporary_manifest, manifest_path)
        return {**record, "preview_path": str(svg_path)}
    except Exception:
        svg_path.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
        raise


def inspect_cad_preview(revision_root: str | Path, preview_root: str | Path,
                        preview_id: str) -> dict:
    if not PREVIEW_ID.fullmatch(preview_id):
        raise ValueError("Expected a 32-character lowercase hexadecimal preview ID.")
    output = _output_root(preview_root)
    name = f"preview-{preview_id}"
    manifest = _inside(output, f"{name}.json")
    svg_path = _inside(output, f"{name}.svg")
    if manifest.stat().st_size > 64 * 1024 or not 0 < svg_path.stat().st_size <= MAX_PREVIEW_BYTES:
        raise ValueError("Preview artifact exceeds size limits.")
    record = json.loads(manifest.read_text(encoding="utf-8"))
    if record.get("preview_id") != preview_id or record.get("svg") != svg_path.name:
        raise ValueError("Preview manifest does not match its artifact.")
    if hashlib.sha256(svg_path.read_bytes()).hexdigest() != record.get("svg_sha256"):
        raise ValueError("Preview SVG hash mismatch.")
    source, _ = _load_revision(_output_root(revision_root), record["revision_id"])
    if source["sha256"] != record.get("source_sha256"):
        raise ValueError("Preview no longer matches its source revision.")
    return {"preview": record, "preview_path": str(svg_path),
            "status": "HASH_VERIFIED_NOT_VISUALLY_APPROVED"}
