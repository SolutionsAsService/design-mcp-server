# Capability audit — 2026-10-05

Audited baseline: `3b411e9` on `main`; canonical checkout `E:\design-mcp-server`. This is an
implementation audit, not an assertion that any particular vehicle design is validated.

| Area | What exists | Evidence / limitation |
| --- | --- | --- |
| MCP surface | Seven tools: `list_assets`, `inspect_asset`, `inspect_stl_geometry`, `get_stl_entities`, `inspect_freecad_model`, `measure_freecad_distance`, `get_scope`; one resource `design://project/assets` | Registered in `design_mcp/server.py`; no MCP prompts or project-specific resources |
| Project/schema | Configured read-only filesystem root; dictionaries returned by tools | No persistent project model, component schema, revision registry, provenance graph or normalized engineering units |
| CAD files | STL topology/metrics and paginated faces/edges/vertices; STEP shape summaries and FCStd object tree via FreeCAD | STL units are unknown. STEP lacks original feature history. FCStd minimum shape distance is unit-tested with mocks, not proven against a real fixture |
| CAD runtime | FreeCAD 1.1.4 bundled Python on D: was previously version/API checked | A previous live fixture command was denied; do not claim end-to-end proof |
| Tests | 15 `unittest` cases pass in the E: virtualenv; catalog/mesh deterministic, FreeCAD subprocess mocked | No CAD fixture integration suite or image/section comparison |
| Dependencies | Python >=3.11, `mcp>=1.9,<2`, standard-library geometry; optional separately configured FreeCAD Python | No NumPy, Pydantic, KiCad, simulator or network research client installed by this project |
| Execution | Read-only path confinement and file-size caps; FreeCAD subprocess timeout 60 s | FreeCAD opening an untrusted file is not sandboxed; server not registered with OpenClaw |

## Gaps and implementation order

1. **CAD revisions:** separate explicitly configured output root; create a simple parametric document, reopen and verify, record source/hash. Preserve inputs. Unit tests and a real FreeCAD fixture are distinct gates.
2. **Closed loop:** reinspection of revision, opt-in copy-on-write parameter edits, render and geometry comparison. No automatic acceptance on shape validity alone.
3. **Structured project state:** immutable resource references, provenance/status/units and invalidation graph. No unverified manufacturer values.
4. **Generic integration adapters:** KiCad inspection and neutral geometry exchange only after live toolchain proof; simulation/analysis/manufacturing depend on validated inputs and are not available now.

## Module plan and external resources

- `design_mcp/cad_write.py`: output-root validation, artifact creation and revision manifests.
- `design_mcp/freecad_worker.py`: bounded CAD operations in FreeCAD's bundled Python, followed by reopen/shape validation.
- `design_mcp/server.py`: opt-in MCP tools; existing read-only calls retain behavior.
- `tests/test_cad_write.py`: invalid input, output-boundary and successful/failed worker cases.
- No new packages are necessary for this increment. FreeCAD on D: is optional and remains separately configured; see README. The main acceptance gate is a real generic box document opened and checked through the adapter.

The broader architecture, prospective capabilities, and dependencies are in `roadmap.md`. They are not exported MCP tools until implemented and verified.

## Phase 1 evidence (2026-10-05)

- `create_box_revision(2, 3, 4)` ran through FreeCAD 1.1.4 bundled Python on D: and saved a new FCStd document plus a SHA-256 manifest under `E:\design-mcp-server\.tmp\revisions`.
- `inspect_revision` verified the artifact hash and reopened the saved document: one valid, closed `Part::Box`, bounds 2 × 3 × 4 mm, volume approximately 24 mm³, and centroid (1, 1.5, 2) mm.
- 19 unit tests pass on the E: Windows checkout. This verifies generic box creation and reinspection, **not** rendering, parameter edits, assemblies, manufacturing suitability, or the earlier distance tool's real-file behavior.

## Tool and resource inventory for the next gates

| Priority | Proposed MCP interface | Dependency | Gate |
| --- | --- | --- | --- |
| Implemented | `create_box_revision`, `inspect_cad_revision` | Separate revision root and D: FreeCAD Python | Generic 2 × 3 × 4 mm FCStd created and reopened; hash checked |
| Next | `revise_box_parameters`, `compare_cad_revisions` | Verified current writer | Original unchanged; before/after dimensions and hashes recorded |
| Next | `render_cad_revision`, `design://project/revisions` | Proven headless renderer and bounded image output | Image can be independently inspected and tied to revision hash |
| Later | `inspect_kicad_project`, `design://project/electronics` | KiCad CLI version/API discovery | Read-only fixture, ERC/DRC evidence, source revision recorded |
| Later | `design://project/current`, `design://project/validation` | Persistent project/provenance schema | Missing data produces UNKNOWN; stale results marked explicitly |

Only `design://project/assets` exists today as an MCP resource. These prospective interfaces are not registered in this increment.
