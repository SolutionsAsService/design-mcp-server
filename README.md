# design-mcp-server

Read-only MCP for inventorying project files and checking basic container integrity for static CAD assets. It is generic and does not model or validate a vehicle, aircraft, component fit, or flight system.

## Scope

Tools list files beneath one configured root, report metadata and SHA-256, and run limited format checks for STL, glTF/GLB, 3MF, and FreeCAD FCStd. STEP/ STP files are hashed only.

No CAD authoring, dimensions, fit/clearance checks, manufacturing advice, component databases, electrical/power/propulsion analysis, mass/CG, control/navigation, simulation, hardware, or flight-test tools are included. No network, subprocess, arbitrary path, or write operations are exposed.

STRUCTURE_VALID means only that supported container checks passed. It is not engineering validation.

## Setup

Python 3.11+:

```powershell
python -m venv .venv
$env:PIP_CACHE_DIR = "$PWD\.cache\pip"
.\.venv\Scripts\python.exe -m pip install -e .
$env:DESIGN_MCP_ASSET_ROOT = "E:\path\to\assets"
.\.venv\Scripts\design-mcp-server.exe
```

The root must exist. The MCP uses stdio. Run tests with `python -m unittest discover -s tests -v`.

## MCP surface

Tools: `list_assets(relative_directory=".")`, `inspect_asset(relative_path)`, `get_scope()`.
Resource: `design://project/assets`.

See `docs/scope.md` for limits and integrity semantics.
