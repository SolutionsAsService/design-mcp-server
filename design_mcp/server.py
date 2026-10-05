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

mcp = FastMCP("design-mcp-server")


def _asset_root() -> Path:
    configured = os.environ.get("DESIGN_MCP_ASSET_ROOT")
    if not configured:
        raise RuntimeError("Set DESIGN_MCP_ASSET_ROOT to an existing directory.")
    root = Path(configured).resolve(strict=True)
    if not root.is_dir():
        raise RuntimeError("DESIGN_MCP_ASSET_ROOT must be a directory.")
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
def get_scope() -> dict:
    """Describe implemented capabilities and fixed read-only boundaries."""
    return {
        "mode": "READ_ONLY_ASSET_CATALOG_AND_CAD_GEOMETRY",
        "network": False,
        "subprocess": "FreeCAD bundled Python only, when configured",
        "writes": False,
        "geometry_formats": ["STL triangulated surface mesh", "STEP BREP via FreeCAD", "FCStd feature tree via FreeCAD"],
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


def main() -> None:
    _asset_root()
    mcp.run()


if __name__ == "__main__":
    main()
