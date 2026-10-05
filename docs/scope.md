# Project scope and implemented boundary

This repository is the long-term civilian design and engineering MCP project. The goal is an evidence-backed, versioned engineering system that can connect requirements, components, CAD, electrical architecture, analysis, simulation, validation, tests, and build documentation. The full roadmap is in roadmap.md.

## Implemented now

- Read-only file inventory and SHA-256 inspection beneath DESIGN_MCP_ASSET_ROOT.
- Bounded integrity checks for STL, glTF/GLB, 3MF, and FreeCAD FCStd containers.
- STL mesh topology and geometric metrics: triangle faces, unique vertices and edges, edge-connected shell count, boundary/non-manifold/orientation-conflict edges, axis-aligned bounds, surface area, surface centroid, and enclosed volume/volume centroid only for a closed consistently oriented mesh.
- Paginated STL face, edge, and vertex records.

STL units are not encoded. Measurements are in raw model coordinates, with units explicitly UNKNOWN. The mesh inspector does not check self-intersections, infer materials/density, calculate mass properties, or establish that a mesh represents a manufacturable part. A closed mesh is not proof of engineering validity.

## Not implemented

FreeCAD/STEP topology, CAD authoring, parametric feature regeneration, assembly constraints, component envelopes, manufacturer data ingestion, drone engineering calculations, KiCad, structural/thermal analysis, simulators/SITL, log analysis, manufacturing, and build package generation are planned, not available tools.

## Execution and path boundaries

The current server is read-only. It has no physical hardware actuation, arbitrary command execution, network access, or file writes. Tool paths must be relative to the configured root; absolute paths, parent traversal, and symlinks are rejected. Asset checks have size and mesh-triangle limits. STRUCTURE_VALID only reports supported file/container checks; it is not engineering validation.
