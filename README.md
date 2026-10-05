# design-mcp-server

A modular MCP engineering project. The current release is a read-only project asset catalog with bounded CAD mesh reasoning; it is the first increment, not the complete drone engineering platform.

## Current tools

- `list_assets(relative_directory=".")` inventories files beneath one configured root.
- `inspect_asset(relative_path)` hashes a file and checks limited STL, glTF/GLB, 3MF, and FCStd container structure.
- `inspect_stl_geometry(relative_path)` reports STL triangle topology, bounds, surface area, and only computes enclosed volume when the mesh is closed and consistently oriented.
- `get_stl_entities(relative_path, entity, offset, limit)` pages faces, unique edges, or vertices.
- `inspect_freecad_model(relative_path)` reads STEP BREP metrics or an FCStd model tree through FreeCAD's bundled Python (optional).
- `get_scope()` reports the implemented boundary.
- Resource: `design://project/assets`.

STL coordinates have unknown units. The mesh tool does not test self-intersections, infer materials, or validate engineering suitability. FreeCAD uses millimetres internally for STEP/FCStd geometry; no material or mass is inferred. No CAD authoring, vehicle engineering, electrical, propulsion, simulation, physical-hardware, or flight-test commands are available yet.

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

### Optional FreeCAD inspection on Windows

Download an official FreeCAD portable release to D:, verify its published SHA-256, and extract it there. Set `DESIGN_MCP_FREECAD_PYTHON` to its `bin\python.exe` (not system Python), and set `TEMP`, `TMP`, and `FREECAD_USER_HOME` to directories on D: before starting the MCP. For the verified FreeCAD 1.1.4 layout on this machine:

```powershell
$env:DESIGN_MCP_FREECAD_PYTHON = 'D:\New folder\OpenClaw\Apps\FreeCAD\1.1.4\FreeCAD_1.1.4-Windows-x86_64-py311\bin\python.exe'
$env:TEMP = 'D:\New folder\OpenClaw\tmp'
$env:TMP = $env:TEMP
$env:FREECAD_USER_HOME = 'D:\New folder\OpenClaw\Apps\FreeCAD\user'
```

Only `.step`, `.stp`, and `.fcstd` files within the configured asset root are accepted. The worker does not save files, but opening untrusted native CAD files through FreeCAD is not sandboxed; use trusted documents. Results are capped at 200 document objects and 60 seconds per inspection.

## Scope and roadmap

See [docs/scope.md](docs/scope.md) and [docs/roadmap.md](docs/roadmap.md) for the full requested product scope, implementation status, dependencies, and phase gates.
