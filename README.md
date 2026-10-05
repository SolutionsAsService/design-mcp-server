# design-mcp-server

A modular MCP engineering project. The current release is a read-only project asset catalog with bounded CAD mesh reasoning; it is the first increment, not the complete drone engineering platform.

## Current tools

- `list_assets(relative_directory=".")` inventories files beneath one configured root.
- `inspect_asset(relative_path)` hashes a file and checks limited STL, glTF/GLB, 3MF, and FCStd container structure.
- `inspect_stl_geometry(relative_path)` reports STL triangle topology, bounds, surface area, and only computes enclosed volume when the mesh is closed and consistently oriented.
- `get_stl_entities(relative_path, entity, offset, limit)` pages faces, unique edges, or vertices.
- `get_scope()` reports the implemented boundary.
- Resource: `design://project/assets`.

STL coordinates have unknown units. The mesh tool does not test self-intersections, infer materials, or validate engineering suitability. STEP files are hashed only. No CAD authoring, vehicle engineering, electrical, propulsion, simulation, physical-hardware, or flight-test commands are available yet.

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

## Scope and roadmap

See [docs/scope.md](docs/scope.md) and [docs/roadmap.md](docs/roadmap.md) for the full requested product scope, implementation status, dependencies, and phase gates.
