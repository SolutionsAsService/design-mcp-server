# Capability audit — 2026-10-05

Baseline before this increment: `6647075` on `main`; canonical Windows checkout `E:\design-mcp-server`.
This audits registered code and observed tests, not an aircraft or manufacturing design.
The earlier seven-tool audit remains recoverable in Git history.

| Area | Current implementation | Evidence and limit |
| --- | --- | --- |
| MCP | 26 tools in `design_mcp/server.py`; four resources (assets, revisions, snapshots, records) | Prior 23-tool Windows stdio handshake passed; three new tools need their own live gate |
| Asset catalog | Read-only path-confined inventory, SHA-256, bounded STL/glTF/GLB/3MF/FCStd container checks | Container checks do not validate engineering suitability |
| Mesh | STL topology, bounded face/edge/vertex paging, bounds/area and conditional volume | STL units unknown; no self-intersection or mass/material inference |
| Native CAD | STEP shape summaries, FCStd object tree, bounded BREP paging and named-shape distance with conditional intersection volume | FreeCAD 1.1.4 portable Python on D: passed generic STEP/FCStd fixtures; zero distance is not clearance certification (`native-cad-verification.md`) |
| CAD transactions | Opt-in generated-box create/edit/ancestor rollback with hash manifests; revision listing and dimension comparison | Live FreeCAD box rollback passed; arbitrary CAD editing, typed project model and cross-process locking absent (`rollback-verification.md`) |
| Provenance snapshots | Opt-in bounded SHA-256 manifests for up to 20 generic asset/revision references; paged listing and change/missing/unknown recheck | Live snapshot of README plus a generated CAD revision returned CURRENT; neither a typed project nor a dependency graph (`snapshot-verification.md`) |
| Typed generic project/evidence | Immutable project records tied to a hash-checked snapshot; at most 20 source/subject evidence links with explicit units and user-attested statuses | Live E: MCP project/evidence flow passed; no independent claim validation or dependency graph (`project-record-verification.md`) |
| Proposed scalar requirements/configuration | V2 immutable project children with up to 20 source-linked requirements and 20 parameters; explicit normalized quantity and strict same-dimension conversions | Four new deterministic tests pass locally; E: MCP gate pending; no requirement satisfaction or independent evidence verification |
| Preview | Hash-linked 640×480 SVG wireframe for generated box revisions | Live export and integrity check passed; visual approval, hidden-line removal and sections absent (`preview-verification.md`) |
| Tests/dependencies | 44 `unittest` tests pass locally; Python >=3.11 and `mcp>=1.9,<2`; optional FreeCAD 1.1.4 on D: | E: run pending for this increment; no new runtime dependency |
| Runtime | Read-only asset root, opt-in separate revision/preview roots, 60-second FreeCAD subprocess limit | FreeCAD file opening is not sandboxed; no physical hardware actuation; no proven OpenClaw registration of the newest tool |

## Gaps and next gated step

1. The snapshot tools/resource passed an E: MCP handshake with generic fixtures. A snapshot is not an engineering project, compatibility result or dependency graph.
2. The typed project/evidence flow passed a Windows MCP client run. Verify the proposed requirement/parameter tools on E: and keep labels distinct from independent verification.
3. Independently inspect the SVG visually; improve rendering and sectioning before claiming a closed visual loop.
4. Any component or assembly work depends on trusted geometry and source-backed specifications. KiCad, analysis, simulation and build outputs remain roadmap items, not exported tools.

See `docs/roadmap.md` for the long-range scope. Do not treat planned interfaces as implemented.
