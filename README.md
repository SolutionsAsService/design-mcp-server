# design-mcp-server

A modular MCP engineering project. The current release is a read-only project asset catalog with an opt-in generic FreeCAD revision writer; it is not a complete vehicle engineering platform.

## Current tools

- `list_assets(relative_directory=".")` inventories files beneath one configured root.
- `inspect_asset(relative_path)` hashes a file and checks limited STL, glTF/GLB, 3MF, and FCStd container structure.
- `inspect_stl_geometry(relative_path)` reports STL triangle topology, bounds, surface area, and only computes enclosed volume when the mesh is closed and consistently oriented.
- `get_stl_entities(relative_path, entity, offset, limit)` pages faces, unique edges, or vertices.
- `inspect_freecad_model(relative_path)` reads STEP BREP metrics or an FCStd model tree through FreeCAD's bundled Python (optional).
- `measure_freecad_distance(relative_path, first_object, second_object)` finds minimum separation between two named FCStd shapes (optional FreeCAD runtime). Zero indicates contact **or** overlap, not verified clearance.
- `create_box_revision(length_mm, width_mm, height_mm)` creates a new parametric FCStd box and a hash/provenance manifest under a separate, explicitly configured revision root; never modifies an input file.
- `inspect_cad_revision(revision_id)` verifies the saved hash and reinspects the FCStd model.
- `revise_box_parameters(parent_revision_id, length_mm, width_mm, height_mm)` creates a new FCStd from a hash-checked generated box, preserving its parent.
- `compare_box_revisions(first_revision_id, second_revision_id)` reports before/after dimensions and direct parentage from hash-checked manifests.
- `get_scope()` reports the implemented boundary.
- Resource: `design://project/assets`.

STL coordinates have unknown units. The mesh tool does not test self-intersections, infer materials, or validate engineering suitability. FreeCAD uses millimetres internally for STEP/FCStd geometry; no material or mass is inferred. Box creation and copy-on-write box edits are the only CAD authoring operations; they do not validate manufacture or physical fit. No vehicle engineering, electrical, propulsion, simulation, physical-hardware, or flight-test commands are available.

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

Only `.step`, `.stp`, and `.fcstd` files within the configured asset root are accepted for inspection. Distance measurement requires `.fcstd` with two existing shape-bearing object names. Inspection does not save files, but opening untrusted native CAD files through FreeCAD is not sandboxed; use trusted documents. Results are capped at 200 document objects, 10 closest point pairs, and 60 seconds per operation.

### Opt-in generic CAD revisions

Set `DESIGN_MCP_REVISION_ROOT` to an **existing, dedicated non-symlink directory** separate from the asset root to enable the revision tools. Keep this root on E: for this project; FreeCAD runtime and temp remain on D:. Each create/edit returns a random revision ID and writes a new `.fcstd` plus a JSON file containing dimensions in mm, SHA-256, parent ID/hash when applicable, and reopen geometry validation. Comparison does not invoke FreeCAD. The write is not a render, assembly check, or manufacturing approval. Treat the revision root as trusted: FreeCAD's process is not an OS sandbox.

## Scope and roadmap

See [docs/capability-audit.md](docs/capability-audit.md), [docs/scope.md](docs/scope.md) and [docs/roadmap.md](docs/roadmap.md) for the capability audit, gaps, full requested product scope, implementation status, dependencies, and phase gates.
