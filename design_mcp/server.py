from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from design_mcp.catalog import inspect_asset as inspect_file
from design_mcp.catalog import list_assets as list_files
from design_mcp.geometry import get_stl_entities as read_stl_entities
from design_mcp.geometry import inspect_stl_geometry as inspect_stl
from design_mcp.freecad import inspect_freecad as read_freecad
from design_mcp.freecad import measure_freecad_distance as read_freecad_distance
from design_mcp.freecad import get_freecad_entities as read_freecad_entities
from design_mcp.cad_write import create_box_revision as write_box_revision
from design_mcp.cad_write import inspect_revision as read_revision
from design_mcp.cad_write import revise_box_parameters as write_box_parameters
from design_mcp.cad_write import compare_box_revisions as compare_box_models
from design_mcp.cad_write import list_revisions as read_revisions
from design_mcp.cad_write import rollback_box_revision as rollback_box_model
from design_mcp.preview import preview_cad_revision as export_revision_preview
from design_mcp.preview import inspect_cad_preview as read_cad_preview

mcp = FastMCP("design-mcp-server")


def _asset_root() -> Path:
    configured = os.environ.get("DESIGN_MCP_ASSET_ROOT")
    if not configured:
        raise RuntimeError("Set DESIGN_MCP_ASSET_ROOT to an existing directory.")
    root = Path(configured).resolve(strict=True)
    if not root.is_dir():
        raise RuntimeError("DESIGN_MCP_ASSET_ROOT must be a directory.")
    return root


def _revision_root() -> Path:
    configured = os.environ.get("DESIGN_MCP_REVISION_ROOT")
    if not configured:
        raise RuntimeError("Set DESIGN_MCP_REVISION_ROOT to an existing dedicated output directory.")
    root = Path(configured)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("DESIGN_MCP_REVISION_ROOT must be an existing non-symlink directory.")
    root = root.resolve(strict=True)
    if root == _asset_root():
        raise RuntimeError("Revision root must differ from the read-only asset root.")
    return root


def _preview_root() -> Path:
    configured = os.environ.get("DESIGN_MCP_PREVIEW_ROOT")
    if not configured:
        raise RuntimeError("Set DESIGN_MCP_PREVIEW_ROOT to an existing dedicated directory.")
    raw = Path(configured)
    if raw.is_symlink() or not raw.is_dir():
        raise RuntimeError("DESIGN_MCP_PREVIEW_ROOT must be an existing non-symlink directory.")
    root = raw.resolve(strict=True)
    if root in {_asset_root(), _revision_root()}:
        raise RuntimeError("Preview root must differ from asset and revision roots.")
    return root


@mcp.tool()
def list_assets(relative_directory: str = ".") -> dict:
    """List file metadata beneath the configured read-only root."""
    return list_files(_asset_root(), relative_directory)


@mcp.tool()
def inspect_asset(relative_path: str) -> dict:
    """Hash an asset and run limited container checks; no dimensions or fit analysis."""
    return inspect_file(_asset_root(), relative_path)


@mcp.tool()
def inspect_stl_geometry(relative_path: str) -> dict:
    """Calculate topology and geometric metrics for a triangulated STL mesh."""
    return inspect_stl(_asset_root(), relative_path)


@mcp.tool()
def get_stl_entities(relative_path: str, entity: str = "faces", offset: int = 0, limit: int = 100) -> dict:
    """Return a bounded page of STL triangle faces, unique edges, or unique vertices."""
    return read_stl_entities(_asset_root(), relative_path, entity, offset, limit)


@mcp.tool()
def inspect_freecad_model(relative_path: str) -> dict:
    """Inspect STEP geometry or an FCStd feature tree through FreeCAD's bundled Python."""
    return read_freecad(_asset_root(), relative_path)


@mcp.tool()
def measure_freecad_distance(relative_path: str, first_object: str, second_object: str) -> dict:
    """Measure the nearest separation between two named FCStd shapes, without modifying the document."""
    return read_freecad_distance(_asset_root(), relative_path, first_object, second_object)


@mcp.tool()
def get_freecad_entities(relative_path: str, entity: str, object_name: str = "",
                         offset: int = 0, limit: int = 25) -> dict:
    """Page bounded STEP/FCStd BREP entity measurements (not a manufacturing validation)."""
    return read_freecad_entities(_asset_root(), relative_path, entity, object_name, offset, limit)


@mcp.tool()
def create_box_revision(length_mm: float, width_mm: float, height_mm: float) -> dict:
    """Opt-in: save a new, parametric FreeCAD box to the separate revision root; never edit inputs."""
    return write_box_revision(_revision_root(), length_mm, width_mm, height_mm)


@mcp.tool()
def inspect_cad_revision(revision_id: str) -> dict:
    """Hash-check and inspect a saved revision from the dedicated output root."""
    return read_revision(_revision_root(), revision_id)


@mcp.tool()
def revise_box_parameters(parent_revision_id: str, length_mm: float, width_mm: float,
                          height_mm: float) -> dict:
    """Save a new parameterized box revision without overwriting its hash-checked parent."""
    return write_box_parameters(_revision_root(), parent_revision_id, length_mm, width_mm, height_mm)


@mcp.tool()
def rollback_box_revision(current_revision_id: str, target_revision_id: str) -> dict:
    """Make a new box child with dimensions from a hash-verified ancestor; preserve both inputs."""
    return rollback_box_model(_revision_root(), current_revision_id, target_revision_id)


@mcp.tool()
def compare_box_revisions(first_revision_id: str, second_revision_id: str) -> dict:
    """Compare dimensions of two hash-checked box revisions without editing either."""
    return compare_box_models(_revision_root(), first_revision_id, second_revision_id)


@mcp.tool()
def list_cad_revisions(offset: int = 0, limit: int = 10) -> dict:
    """Page hash-verified CAD revision summaries; flag missing or altered artifacts."""
    return read_revisions(_revision_root(), offset, limit)


@mcp.tool()
def preview_cad_revision(revision_id: str) -> dict:
    """Export bounded, CAD-derived SVG wireframe into a dedicated scratch root."""
    return export_revision_preview(_revision_root(), _preview_root(), revision_id)


@mcp.tool()
def inspect_cad_preview(preview_id: str) -> dict:
    """Verify preview/source hashes; visual interpretation remains a separate review step."""
    return read_cad_preview(_revision_root(), _preview_root(), preview_id)


@mcp.tool()
def get_scope() -> dict:
    """Describe implemented capabilities and write opt-in boundary."""
    return {
        "mode": "READ_ONLY_ASSET_CATALOG_WITH_OPT_IN_CAD_REVISIONS",
        "network": False,
        "subprocess": "FreeCAD bundled Python only, when configured",
        "writes": "new generic FCStd revisions and SVG previews only with separate configured output roots",
        "geometry_formats": ["STL triangulated surface mesh", "STEP BREP via FreeCAD", "FCStd feature tree and shape distance via FreeCAD"],
        "coordinate_units": "Unknown for STL; the format contains no unit metadata.",
        "self_intersection_test": False,
        "vehicle_analysis": False,
        "container_checks": [".stl", ".gltf", ".glb", ".3mf", ".fcstd"],
        "hashed_only": ["other"],
    }


@mcp.resource("design://project/assets")
def project_assets() -> str:
    """Return the configured root's file inventory."""
    return json.dumps(list_files(_asset_root()), sort_keys=True)


@mcp.resource("design://project/revisions")
def project_revisions() -> str:
    """Return the first bounded page of opt-in CAD revisions, or configuration required."""
    if not os.environ.get("DESIGN_MCP_REVISION_ROOT"):
        return json.dumps({"status": "CONFIGURATION_REQUIRED", "revisions": []})
    return json.dumps(read_revisions(_revision_root()), sort_keys=True)


def main() -> None:
    _asset_root()
    mcp.run()


if __name__ == "__main__":
    main()
