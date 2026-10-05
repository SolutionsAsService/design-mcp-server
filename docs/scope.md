# Project scope and implemented boundary

This repository is the long-term civilian design and engineering MCP project. The goal is an evidence-backed, versioned engineering system that can connect requirements, components, CAD, electrical architecture, analysis, simulation, validation, tests, and build documentation. The full roadmap is in roadmap.md.

## Implemented now

- Read-only file inventory and SHA-256 inspection beneath DESIGN_MCP_ASSET_ROOT.
- Bounded integrity checks for STL, glTF/GLB, 3MF, and FreeCAD FCStd containers.
- STL mesh topology and geometric metrics: triangle faces, unique vertices and edges, edge-connected shell count, boundary/non-manifold/orientation-conflict edges, axis-aligned bounds, surface area, surface centroid, and enclosed volume/volume centroid only for a closed consistently oriented mesh.
- Paginated STL face, edge, and vertex records.
- Read-only STEP/FCStd model summaries and bounded BREP face/edge/vertex/solid/shell pages through configured FreeCAD bundled Python; FCStd named-shape minimum distance distinguishes measurable volumetric intersection from zero-distance contact/ambiguity on valid closed solids. The generic STEP/FCStd live-fixture gate passed; see native-cad-verification.md.
- Opt-in creation, copy-on-write parameter revision and ancestor rollback of a generated FreeCAD box under a separate revision root, with manifests, hash-checked reinspection, lineage verification and dimension comparison; no modification of existing source assets.
- Opt-in SVG wireframe export for generated box revisions to a third scratch root, with source/preview hashes and non-visual integrity reinspection. This is a CAD-derived projection, not a photorealistic render.
- Opt-in bounded project snapshots referencing SHA-256-checked assets and CAD revisions, with snapshot listing and content-change status; this is a provenance index, not a typed project or an engineering dependency graph.
- Opt-in typed, immutable generic project records tied to one snapshot, with source/subject evidence links and user-attested statuses/explicit supported units. Directly changed references trigger reinspection flags, not automatic validation or a general dependency graph.

STL units are not encoded. Measurements are in raw model coordinates, with units explicitly UNKNOWN. The mesh inspector does not check self-intersections, infer materials/density, calculate mass properties, or establish that a mesh represents a manufacturable part. A closed mesh is not proof of engineering validity.

## Not implemented

Unbounded FreeCAD/STEP entity access, arbitrary CAD editing, parametric feature regeneration beyond the single box, typed requirements/configuration, unit conversions, assembly constraints, component envelopes, manufacturer data ingestion, drone engineering calculations, KiCad, structural/thermal analysis, simulators/SITL, log analysis, manufacturing, and build package generation are not available tools. See the target architecture and gates in roadmap.md.

## Execution and path boundaries

Asset reads remain read-only. New generic CAD documents may only be written under the explicitly configured revision root; it has no physical hardware actuation, arbitrary command execution, or network access. Asset paths must be relative to the configured root; absolute paths, parent traversal, and symlinks are rejected. Asset checks have size and mesh-triangle limits. STRUCTURE_VALID only reports supported file/container checks; it is not engineering validation.
