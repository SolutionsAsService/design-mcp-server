# Copy-on-write box rollback verification — 2026-10-05

Canonical checkout: `E:\design-mcp-server`, commit `97bf3b4`; FreeCAD 1.1.4 bundled
Python on D:. Generated artifacts live in the ignored `.tmp\revisions` and
`.tmp\previews` directories. These are disposable generic boxes, not an aircraft.

- Created a 2 × 3 × 4 mm parametric box revision, then a 5 × 3 × 4 mm child.
- Rolled the child back to its ancestor's dimensions by creating a **new** child.
  The new manifest records `operation=rollback_box`, current parent ID/hash,
  ancestor target ID/hash, and dimensions 2 × 3 × 4 mm. Neither earlier model
  was overwritten.
- Reopened the new FCStd with the FreeCAD adapter: bounding-box extents were
  [2, 3, 4] mm and enclosed volume approximately 24 mm³. Revision comparison
  reported a -3 mm change in length from the immediate parent.
- Generated a wireframe SVG of the rolled-back revision; preview inspection
  returned `HASH_VERIFIED_NOT_VISUALLY_APPROVED` with 12 tessellation triangles.
- All 31 unit tests passed locally and on the E: checkout before the live run;
  unit tests also reject non-ancestor rollback, tampered parent hash, and target
  manifest dimensions inconsistent with its reopened model.

This proves generic box rollback and provenance linkage on this FreeCAD runtime.
It is not arbitrary document undo, an atomic multi-process transaction, a
visually reviewed preview, assembly clearance, or manufacturing approval. A
failed worker cannot repair a source file modified by an untrusted process;
the revision root must remain trusted. Visual review and broader project
manifests remain roadmap gates.
