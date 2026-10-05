# Capability audit — 2026-10-05

Baseline before this increment: `6647075` on `main`; canonical Windows checkout `E:\design-mcp-server`.
This audits registered code and observed tests, not an aircraft or manufacturing design.
The earlier seven-tool audit remains recoverable in Git history.

| Area | Current implementation | Evidence and limit |
| --- | --- | --- |
| MCP | 19 tools in `design_mcp/server.py`; three resources: `design://project/assets`, `design://project/revisions`, `design://project/snapshots` | Registered in code; current increment still needs a live MCP tool-list check |
| Asset catalog | Read-only path-confined inventory, SHA-256, bounded STL/glTF/GLB/3MF/FCStd container checks | Container checks do not validate engineering suitability |
| Mesh | STL topology, bounded face/edge/vertex paging, bounds/area and conditional volume | STL units unknown; no self-intersection or mass/material inference |
| Native CAD | STEP shape summaries, FCStd object tree, bounded BREP paging and named-shape distance with conditional intersection volume | FreeCAD 1.1.4 portable Python on D: passed generic STEP/FCStd fixtures; zero distance is not clearance certification (`native-cad-verification.md`) |
| CAD transactions | Opt-in generated-box create/edit/ancestor rollback with hash manifests; revision listing and dimension comparison | Live FreeCAD box rollback passed; arbitrary CAD editing, typed project model and cross-process locking absent (`rollback-verification.md`) |
| Provenance snapshots | Opt-in bounded SHA-256 manifests for up to 20 generic asset/revision references; paged listing and change/missing/unknown recheck | Four new deterministic tests pass locally; a snapshot is neither a typed project nor a dependency graph |
| Preview | Hash-linked 640×480 SVG wireframe for generated box revisions | Live export and integrity check passed; visual approval, hidden-line removal and sections absent (`preview-verification.md`) |
| Tests/dependencies | 35 `unittest` tests pass locally; Python >=3.11 and `mcp>=1.9,<2`; optional FreeCAD 1.1.4 on D: | E: test run pending for this increment; no KiCad adapter, simulator, Pydantic/NumPy or network research client required |
| Runtime | Read-only asset root, opt-in separate revision/preview roots, 60-second FreeCAD subprocess limit | FreeCAD file opening is not sandboxed; no physical hardware actuation; no proven OpenClaw registration of the newest tool |

## Gaps and next gated step

1. Prove the new snapshot tools and resource through the MCP on E: using generic fixtures. A snapshot is not an engineering project, compatibility result or dependency graph.
2. Extend to typed project/evidence records and explicit units after the snapshot integrity gate. Preserve missing data as `UNKNOWN`.
3. Independently inspect the SVG visually; improve rendering and sectioning before claiming a closed visual loop.
4. Any component or assembly work depends on trusted geometry and source-backed specifications. KiCad, analysis, simulation and build outputs remain roadmap items, not exported tools.

See `docs/roadmap.md` for the long-range scope. Do not treat planned interfaces as implemented.
