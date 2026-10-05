# design-mcp-server

A modular MCP engineering project. The current release provides a read-only asset catalog with opt-in generic FreeCAD revisions, bounded provenance snapshots and immutable generic project records; it is not a complete vehicle engineering platform.

## Current tools

- `list_assets(relative_directory=".")` inventories files beneath one configured root.
- `inspect_asset(relative_path)` hashes a file and checks limited STL, glTF/GLB, 3MF, and FCStd container structure.
- `inspect_stl_geometry(relative_path)` reports STL triangle topology, bounds, surface area, and only computes enclosed volume when the mesh is closed and consistently oriented.
- `get_stl_entities(relative_path, entity, offset, limit)` pages faces, unique edges, or vertices.
- `inspect_freecad_model(relative_path)` reads STEP BREP metrics or an FCStd model tree through FreeCAD's bundled Python (optional).
- `get_freecad_entities(relative_path, entity, object_name="", offset=0, limit=25)` pages BREP faces, edges, vertices, shells and solids. FCStd requires an object name; STEP does not. Maximum 50 records.
- `inspect_cad_envelopes(relative_path, object_names, minimum_gap_mm=0)` reads up to eight named FCStd object bounds, returns pairwise AABB separation lower bounds and source SHA-256. Missing bounds and intersecting boxes return `UNKNOWN`, not a collision or fit verdict.
- `register_component_candidate(part_output, footprint_output)` stores bounded caller-forwarded outputs shaped like `pcbparts.jlc_get_part` and a single result from `kicad.library.search`, without certifying their pairing or dimensions.
- `inspect_component_candidate(candidate_id)` and `list_component_candidates(offset=0, limit=10)` hash-check stored candidates and report missing envelope/compatibility as UNKNOWN.
- `create_assembly_manifest(name, instances)` records up to 20 candidate instances, finite mm positions and parent hierarchy; `inspect_assembly_manifest(assembly_id)` checks references but always reports fit UNKNOWN without source-backed envelopes. `list_assembly_manifests` pages hierarchy summaries.
- `measure_freecad_distance(relative_path, first_object, second_object)` finds minimum separation between two named FCStd shapes (optional FreeCAD runtime). For valid closed solids at zero distance it also reports boolean intersection volume: positive volume identifies volumetric overlap; zero volume does **not** distinguish contact from numerical coincidence. Non-solids or failed booleans report an unknown relationship, not verified clearance.
- `create_box_revision(length_mm, width_mm, height_mm)` creates a new parametric FCStd box and a hash/provenance manifest under a separate, explicitly configured revision root; never modifies an input file.
- `inspect_cad_revision(revision_id)` verifies the saved hash and reinspects the FCStd model.
- `revise_box_parameters(parent_revision_id, length_mm, width_mm, height_mm)` creates a new FCStd from a hash-checked generated box, preserving its parent.
- `rollback_box_revision(current_revision_id, target_revision_id)` creates a **new child** using dimensions from a hash-linked, reinspected box ancestor; neither the current nor target model is overwritten. This is a limited parametric rollback, not arbitrary CAD undo.
- `compare_box_revisions(first_revision_id, second_revision_id)` reports before/after dimensions and direct parentage from hash-checked manifests.
- `list_cad_revisions(offset=0, limit=10)` pages revision summaries and flags missing or altered models as `INVALID` (maximum page size 20).
- `preview_cad_revision(revision_id)` exports a CAD-tessellated, isometric SVG wireframe under a separate preview root, linked to the revision hash.
- `inspect_cad_preview(preview_id)` checks the saved preview and source hashes; it does not approve the image visually.
- `create_project_snapshot(name, asset_paths, revision_ids)` records up to 20 hashed generic asset/CAD references in a new immutable manifest under the revision root.
- `inspect_project_snapshot(snapshot_id)` rechecks those references, reporting `CURRENT`, `STALE`, or `UNKNOWN` and the references needing reinspection; `CURRENT` is **not** design approval.
- `list_project_snapshots(offset=0, limit=10)` pages integrity-checked snapshot summaries; corrupt manifests are marked `INVALID`.
- `create_project_record(name, description, snapshot_id)` writes a typed immutable generic project record tied to a `CURRENT` snapshot.
- `add_project_evidence(project_id, subject_kind, subject_reference, source_asset_path, claim, evidence_status, value=None, unit=None)` creates a new project record linked to its parent with a source-backed, user-attested claim about a snapshot asset or CAD revision.
- `inspect_project_record(project_id)` rechecks immediate parent and snapshot hashes, then flags directly impacted evidence links for reinspection; it does not verify claims.
- `list_project_records(offset=0, limit=10)` pages hash-checked project records.
- `add_project_requirement(project_id, key, description, comparator, value, unit, source_asset_path)` appends an unvalidated `AT_MOST`, `AT_LEAST` or `EQUAL` scalar requirement to a **new** project revision.
- `add_project_parameter(project_id, key, value, unit, source_asset_path)` appends a source-linked scalar configuration parameter in a new revision.
- `convert_quantity(value, from_unit, to_unit)` converts supported, dimensionally compatible units without asserting the value is correct.
- `get_scope()` reports the implemented boundary.
- Resources: `design://project/assets`, `design://project/revisions`, `design://project/snapshots`, `design://project/records`, `design://components/candidates` and `design://assembly/manifests` (first page; the latter five require an output root).

STL coordinates have unknown units. The mesh tool does not test self-intersections, infer materials, or validate engineering suitability. FreeCAD uses millimetres internally for STEP/FCStd geometry; no material or mass is inferred. Box creation and copy-on-write box edits are the only CAD authoring operations; they do not validate manufacture or physical fit. No vehicle engineering, electrical, propulsion, simulation, physical-hardware, or flight-test commands are available.

Snapshot manifests retain content hashes and the requested references only: no typed requirements, component data, assembly claims, or dependency graph. Asset paths are confined to the configured root; output is confined to the revision root. A changed or missing reference is `STALE`; an unsafe/unreadable reference is `UNKNOWN`. The manifest hash detects accidental alteration within this trusted root, not malicious rewriting with a recomputed hash.

Project records are append-only revisions with a name, description, snapshot link and up to 20 typed evidence links. Each link has a subject (`asset` or `cad_revision`), an existing source asset, a user-supplied claim/status and optional finite numeric value plus explicit unit (`mm`, `mm2`, `mm3`, `m`, `m2`, `m3`, `g`, `kg`, `V`, `A`, `W`, `Wh`, `N`). Even `VERIFIED` is **user-attested, not independently verified**. Direct source or subject changes yield `RECHECK`; no claim evaluation, dependency graph or engineering approval is implied. Do not write records from untrusted parties into the revision root.

Project record schema v2 also accepts up to 20 proposed scalar requirements and 20 configuration quantities, each tied to an asset in the same snapshot. Values retain input units and an explicit calculated canonical conversion (length m, area m2, volume m3, mass kg; V/A/W/Wh/N unchanged). No requirements are automatically checked; source changes mark directly linked entries `RECHECK`. Prior v1 project manifests remain readable and new edits make a v2 child without rewriting the v1 parent. No unit inference, dependency graph, CAD regeneration or independent evidence verification is provided.

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

Only `.step`, `.stp`, and `.fcstd` files within the configured asset root are accepted for inspection. Distance measurement requires `.fcstd` with two existing shape-bearing object names. Entity pages are geometric records, not drawings or assembly validation. Inspection does not save files, but opening untrusted native CAD files through FreeCAD is not sandboxed; use trusted documents. Results are capped at 200 document objects, 10 closest point pairs, and 60 seconds per operation.

The FCStd envelope tool uses existing document object bounds and tree parents. A positive AABB gap is a conservative geometric distance lower bound; an overlapping AABB or missing shape has **UNKNOWN** fit/collision status. This is not a manufacturer-sourced component envelope, instance/constraint model, tolerance analysis, or design approval. Reinspect the source if its returned SHA-256 changes.

External MCP outputs enter through an explicit caller handoff: the design server never calls other MCP servers, looks up stock or places orders itself. Candidate records hash the forwarded payloads and label them unauthenticated; the footprint pairing and pin map remain unverified. Assembly manifests do not add dimensions, CAD geometry, connector access or validated fit. See [docs/integration-plan.md](docs/integration-plan.md) for the guarded coordination workflow.

### Opt-in generic CAD revisions

Set `DESIGN_MCP_REVISION_ROOT` to an **existing, dedicated non-symlink directory** separate from the asset root to enable the revision tools. Keep this root on E: for this project; FreeCAD runtime and temp remain on D:. Each create/edit returns a random revision ID and writes a new `.fcstd` plus a JSON file containing dimensions in mm, SHA-256, parent ID/hash when applicable, and reopen geometry validation. Comparison does not invoke FreeCAD. Listings sort by ID, not creation time, and verify hashes only on the requested page; `INVALID` is an integrity status, not an engineering judgment. The write is not a render, assembly check, or manufacturing approval. Treat the revision root as trusted: FreeCAD's process is not an OS sandbox.

Rollback requires the target to be an ancestor of the current revision. It checks each lineage link and model hash, reopens the target, compares actual box bounds with recorded dimensions, and creates another hash-linked FCStd revision from the current model. The saved model is geometry-validated only; undoing arbitrary source files, visual approval and a transaction-safe cross-process lock are not implemented.

For SVG previews, also set `DESIGN_MCP_PREVIEW_ROOT` to an **existing, dedicated non-symlink scratch directory** distinct from both roots (for example, `E:\design-mcp-server\.tmp\previews`). The worker uses the real FreeCAD shape's tessellation and emits up to 5,000 triangles onto a 640 × 480 isometric wireframe; the preview is capped at 2 MiB and has a SHA-256 sidecar. No hidden-surface removal, material depiction, lighting, sectioning or human visual approval is implied. Inspect the SVG in a viewer before accepting a visual claim.

## Scope and roadmap

See [docs/capability-audit.md](docs/capability-audit.md), [docs/scope.md](docs/scope.md) and [docs/roadmap.md](docs/roadmap.md) for the capability audit, gaps, full requested product scope, implementation status, dependencies, and phase gates.
