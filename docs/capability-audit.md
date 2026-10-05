# Capability audit — 2026-10-05

Baseline before this increment: `6647075` on `main`; canonical Windows checkout `E:\design-mcp-server`.
This audits registered code and observed tests, not an aircraft or manufacturing design.
The earlier seven-tool audit remains recoverable in Git history.

| Area | Current implementation | Evidence and limit |
| --- | --- | --- |
| MCP | 33 tools in `design_mcp/server.py`; six resources (assets, revisions, snapshots, records, candidates, assemblies) | E: stdio handoff exercised candidate and assembly tools and candidate resource; FCStd envelope MCP gate remains pending |
| Asset catalog | Read-only path-confined inventory, SHA-256, bounded STL/glTF/GLB/3MF/FCStd container checks | Container checks do not validate engineering suitability |
| Mesh | STL topology, bounded face/edge/vertex paging, bounds/area and conditional volume | STL units unknown; no self-intersection or mass/material inference |
| Native CAD | STEP shape summaries, FCStd object tree, bounded BREP paging and named-shape distance with conditional intersection volume | FreeCAD 1.1.4 portable Python on D: passed generic STEP/FCStd fixtures; zero distance is not clearance certification (`native-cad-verification.md`) |
| Assembly geometry slice | Read-only FCStd object AABBs, tree parents, source hash and conservative pairwise gap lower bound | Four tests pass locally and on E:; FreeCAD reopened the four-object fixture, but the envelope MCP call timed out and a later direct run was denied; live envelope gate pending (`envelope-verification.md`) |
| Cross-MCP candidate/hierarchy handoff | Bounded, hash-linked caller-forwarded pcbparts and KiCad search records; immutable candidate instances and parent hierarchy | Five deterministic tests plus E: stdio MCP handoff passed with observed identifier subset. No direct server-to-server access, authenticated provider provenance, sourced dimensions, pad mapping or fit claim (`integration-plan.md`) |
| CAD transactions | Opt-in generated-box create/edit/ancestor rollback with hash manifests; revision listing and dimension comparison | Live FreeCAD box rollback passed; arbitrary CAD editing, typed project model and cross-process locking absent (`rollback-verification.md`) |
| Provenance snapshots | Opt-in bounded SHA-256 manifests for up to 20 generic asset/revision references; paged listing and change/missing/unknown recheck | Live snapshot of README plus a generated CAD revision returned CURRENT; neither a typed project nor a dependency graph (`snapshot-verification.md`) |
| Typed generic project/evidence | Immutable project records tied to a hash-checked snapshot; at most 20 source/subject evidence links with explicit units and user-attested statuses | Live E: MCP project/evidence flow passed; no independent claim validation or dependency graph (`project-record-verification.md`) |
| Proposed scalar requirements/configuration | V2 immutable project children with up to 20 source-linked requirements and 20 parameters; explicit normalized quantity and strict same-dimension conversions | Live E: MCP calls passed; no requirement satisfaction or independent evidence verification (`quantity-verification.md`) |
| Preview | Hash-linked 640×480 SVG wireframe for generated box revisions | Live export and integrity check passed; visual approval, hidden-line removal and sections absent (`preview-verification.md`) |
| Tests/dependencies | 54 `unittest` tests on E: passed, including one SDK stdio handoff; WSL local run passes 53 and skips SDK smoke when MCP is absent. Python >=3.11 and `mcp>=1.9,<2`; optional FreeCAD 1.1.4 on D: | No new runtime dependency |
| Runtime | Read-only asset root, opt-in separate revision/preview roots, 60-second FreeCAD subprocess limit | FreeCAD file opening is not sandboxed; no physical hardware actuation; no proven OpenClaw registration of the newest tool |

## Gaps and next gated step

1. The snapshot tools/resource passed an E: MCP handshake with generic fixtures. A snapshot is not an engineering project, compatibility result or dependency graph.
2. Proposed scalar requirement/parameter tools passed E: MCP calls. Next add bounded requirement satisfaction checks only when explicitly requested and supplied with source-backed observations; do not infer validation from a proposal.
3. Independently inspect the SVG visually; improve rendering and sectioning before claiming a closed visual loop.
4. Any component or assembly work depends on trusted geometry and source-backed specifications. KiCad, analysis, simulation and build outputs remain roadmap items, not exported tools.
5. `kicad-cli` is not on the Windows node PATH; locate and verify an installed CLI or explicitly install one on D: before a KiCad adapter claims ERC/DRC or STEP output.
6. Design a source-backed envelope schema and independently verify manufacturer drawing dimensions and KiCad pad mapping before fit checks. The E: handoff fixture proves MCP plumbing only; do not infer physical dimensions from a package code or footprint name.

See `docs/roadmap.md` for the long-range scope. Do not treat planned interfaces as implemented.
