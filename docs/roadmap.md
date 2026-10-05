# Design MCP server roadmap

## Product goal

Build a modular MCP engineering system for civilian aircraft and other mechanical projects, with a first practical target of supporting multirotor engineering. Project state and evidence live in version-controlled data, not only in conversation. Every value carries units, provenance, and verification status. The server separates analysis, simulation, CAD operations, and physical hardware; physical actuation is not exposed by default.

## Complete product scope

### CAD reasoning and geometry
- Inspect model, part, body, face, edge, vertex, solid, shell, plane, axis, and coordinate-system trees where the source format preserves them.
- Measure distance, angle, radius, diameter, area, volume, thickness, clearance, offset, and alignment.
- Report bounds, center of mass, inertia, principal axes, and material properties only when geometry, units, and material evidence support the result.
- Support STL/3MF/glTF mesh analysis separately from BREP/STEP/FreeCAD feature-tree analysis; label limitations and units per format.

### CAD authoring and parametric design
- Create documents, bodies, parts, sketches, datum geometry, primitives, extrusions, revolutions, lofts, sweeps, and supported boolean/finishing features.
- Modify parameters and sketch constraints while preserving feature history; provide proposed changes, validation, and saved revisions rather than silent destructive edits.
- Move, rotate, scale, align, attach, mirror, pattern, array, fillet, chamfer, shell, thicken, offset, and create holes/threads only through a verified CAD adapter.
- Save to a new revision; inspect, render, measure, section, and validate the result before approval.

### Assemblies and envelopes
- Represent assemblies, subassemblies, component instances, placements, constraints, mounting interfaces, and service access.
- Check fit, collision/interference, clearances, fastener/connector/tool access, cable routing, and maintenance access with stated tolerances.
- Maintain component envelopes for exact CAD, simplified CAD, or sourced engineering envelopes. Never label guessed envelope fields as verified.

### Component and research graph
- Keep components with manufacturer, exact MPN, category, source-backed mass/dimensions/electrical/mechanical interfaces, connectors, thermal/material limits, CAD, datasheets, drawings, revision, confidence, and verification status.
- Support motors, propellers, ESCs, batteries, flight controllers, navigation/radio/telemetry, sensors, cameras, power devices, connectors, wiring, fasteners, bearings, shafts, structural materials, vibration mounts, antennas, and installation hardware.
- Ingest manufacturer pages, datasheets, drawings, STEP/STL models, application notes, CAD libraries, and measured project data with URL, retrieval time, revision/page/evidence and confidence. Never fabricate MPNs or silently substitute marketplace claims.

### Engineering analysis
- Track requirements, configuration, components, mass budget, mass distribution, CG, CG envelope, inertia, and revision-to-revision change.
- Model electrical power graphs and wiring, then calculate supported current, power, energy, voltage drop, resistance, wire/connector/regulator/battery checks with explicit units and evidence.
- Compare propulsion options from manufacturer or measured motor/propeller test data; separate manufacturer data, measured data, calculated results, simulation, estimates, and assumptions.
- Add thermal, vibration, structural load, stress/deflection, fastener/mount-load, material comparison, and tolerance-stack methods only with bounded assumptions and validation gates. Prefer established solvers/adapters over an unverified home-grown FEA/CFD solver.

### Electronics, simulation, tests, and delivery
- Integrate KiCad project/schematic/PCB/netlist/BOM/ERC/DRC/STEP flows and map verified PCB geometry into CAD.
- Provide adapter interfaces for ArduPilot/PX4 and selected SITL/simulator systems (evaluate Gazebo, JSBSim, Webots and others by maintenance, fidelity, and platform support).
- Ingest simulation and flight logs; analyze attitude, battery, vibration, GPS, temperature, controller output, and failsafe events, linked to a project revision. Simulation is never confused with physical actuation.
- Maintain test plans/results, design decisions, open issues, validation reports, CAD/engineering resources, MCP resources/prompts, revision history, manufacturing/DFM checks, BOM/wiring/assembly instructions, and reproducible build packages.
- Propagate engineering changes: identify impacted CAD, mass/CG, power/wiring, propulsion, simulation, BOM, validation, and retests; mark stale results rather than presenting them as current.

## Full design-MCP architecture (planned, not implemented)

The durable state should be a project manifest referencing immutable source assets, revisions,
evidence records, and validation runs. Independent adapters should expose capabilities rather
than silently substitute a different CAD kernel, solver, or data source. The API should expose
structured status (`AVAILABLE`, `CONFIGURATION_REQUIRED`, `UNAVAILABLE`) for each adapter.

| Layer | Planned responsibility | Acceptance gate |
| --- | --- | --- |
| Project and provenance | Stable IDs, source URLs/hashes, measured vs derived values, explicit units, revision snapshots | Reopen a revision and reconstruct its evidence without conversational state |
| CAD and geometry | FreeCAD/STEP topology, bounded measurements, immutable edit transactions, render and reinspection | Original preserved; updated model reopens, measurements and preview match revision |
| Assembly and components | Hierarchies, instances, sourced envelopes, attachment interfaces, tolerance-aware fit | Missing dimensions yield UNKNOWN, never a fabricated pass |
| Electronics | KiCad read/validate, traceable board model and neutral-format exchange | ERC/DRC outputs and imported geometry retain source revision |
| Generic analysis | Mass properties only with known units/materials, structural/thermal solver adapters | Inputs and applicability bounded; calculations reproducible |
| Validation and delivery | Evidence-linked findings, staleness propagation, export manifests | Changing a source invalidates all affected derived results |

The long-range request also mentions aircraft-specific propulsion, power architecture,
autopilot, SITL/HITL, flight-log analysis, and flight build packages. These are **not**
implemented or promised by the present static-design server; they are not prerequisites
for the generic CAD development gates here. Do not mistake roadmap text for exposed tools.

### Next generic CAD milestones

1. STEP and FCStd inspection passed with actual generic fixtures on the target Windows runtime (2026-10-05).
2. Bounded FCStd shape-to-shape separation now reports positive volumetric intersection separately
   from zero distance without measurable intersection. This is not a contact or clearance certification;
   non-solids and failed booleans remain unknown. Live fixture acceptance passed for closed boxes.
3. Read-only BREP entity paging and a hash-linked, bounded SVG wireframe preview are implemented.
   Section views and visually inspected render output remain future acceptance gates.
4. Continue from the copy-on-write box edit and dimension comparison with preview and
   visual inspection; ancestor-only parametric box rollback creates a verified child revision.
   Arbitrary CAD undo remains unavailable; edits reopen geometry but do not render or certify fit.
5. Extend the bounded CAD revision index and resource with project/provenance manifests and
   change-impact tracking before component or assembly claims. Current index is not a project model.

## Delivery sequence and gates

1. **Phase 0 - MCP foundation (complete):** stdio server, configured read-only root, safe path resolution, SHA-256, file/container checks, unit tests.
2. **Phase 1A - mesh CAD reasoning (complete):** bounded STL topology/entity queries and geometric metrics. Gate: deterministic closed/open mesh tests; unknown units remain explicit; no unsupported physical claims.
3. **Phase 1B - native CAD reasoning (bounded implementation):** read-only FreeCAD document/model tree and BREP summaries, plus FCStd shape-to-shape separation and conditional solid intersection volume. FreeCAD 1.1.4 bundled Python on D: passed generic STEP/FCStd live fixtures; material properties, feature history from STEP, section views and general engineering clearance remain unavailable.
4. **Phase 1C - CAD change transactions (in progress):** dedicated output root, hash manifest, parent-preserving box parameter edits, ancestor-only box rollback, reopen verification and dimension comparison; visually approved rendering and arbitrary source-copy edits/undo are not yet available.
5. **Phase 2 - project and provenance core:** typed project/configuration/requirements, component and resource schemas, unit normalization, confidence/provenance, revision and change-impact graph.
6. **Phase 3 - component envelopes and assembly:** manufacturer-backed records, CAD/envelope links, assembly instances and fit/access/collision checks. Requires validated geometry and component data.
7. **Phase 4 - engineering analysis:** mass/CG/inertia, electrical/power/wiring, propulsion test-data ingestion, thermal/vibration/structural methods. Each calculator has unit tests, explicit evidence status, and bounded applicability.
8. **Phase 5 - electronics and manufacturing adapters:** KiCad inspection/validation/STEP mapping; drawing/BOM/wiring/manufacturing outputs and tolerance/DFM checks.
9. **Phase 6 - simulation and logs:** choose one maintained SITL stack after toolchain verification; connect model state, mass/CG/inertia and propulsion data; log ingestion and analysis.
10. **Phase 7 - design review and package:** evidence-linked review, change propagation, MCP resources/prompts/status, reproducible build package and end-to-end acceptance demonstration.

## Current blockers and next checks

- FreeCAD 1.1.4 on D: passed real STEP/FCStd generic fixture inspection, BREP face paging, and separated/touching/overlapping box checks on 2026-10-05 (see native-cad-verification.md); arbitrary real assemblies and visual previews remain unverified.
- STEP shape summaries and bounded BREP paging are implemented; native feature histories, material and physical mass properties are unavailable, and CAD editing is limited to generated parametric boxes.
- No verified drone project/component dataset is bundled; the tools must not fabricate example manufacturer specifications.
- End-to-end CAD edit/render/inspect/rollback is a future acceptance gate, not a current capability. Generic box creation, parent-preserving edit/reinspection, and a hash-linked SVG wireframe export passed live FreeCAD fixture tests on 2026-10-05. Ancestor-only box rollback needs its own live gate. The preview was not visually reviewed; hidden surfaces and sections are not handled.
