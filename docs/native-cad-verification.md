# Native CAD fixture verification — 2026-10-05

Canonical checkout: `E:\design-mcp-server` at `6b959ca`. Runtime: FreeCAD 1.1.4
portable bundled Python on D:. These were disposable **generic boxes** in the ignored
`.tmp\fixtures` directory, not imported project designs or component data.

- Created `geometry.fcstd` in FreeCAD with four `Part::Box` objects: First at the
  origin (2 × 3 × 4 mm), Separated at x=4 mm, Touching at x=2 mm and Overlapping
  at x=1.5 mm. Exported First to `box.step` with FreeCAD.
- Called the public Python adapter `inspect_freecad` on both formats. STEP returned
  one valid closed solid, 2 × 3 × 4 mm bounds, ~24 mm³ enclosed volume and a
  (1, 1.5, 2) mm volume centroid. FCStd returned four document objects.
- `get_freecad_entities(..., "box.step", "faces", limit=2)` returned two of six
  bounded face records and `has_more=true`.
- `measure_freecad_distance` on First/Separated returned `SEPARATED`, 2 mm; on
  First/Touching returned `ZERO_DISTANCE_NO_VOLUME_OVERLAP`, 0 mm and 0 mm³;
  on First/Overlapping returned `VOLUMETRIC_OVERLAP`, 0 mm and ~6 mm³.
- All 30 unit tests passed locally and in the E: checkout before the live call.

The STEP export imports as a compound in FreeCAD 1.1.4; this exercise exposed
that a compound does not have a direct `CenterOfMass` attribute. The adapter now
reports a weighted centroid only when the volume of its valid closed solid parts
agrees with the compound volume. This is a geometric centroid, **not mass**.

This proves the adapter on these real CAD fixtures, not arbitrary assembly
correctness, service clearance, surface-only overlap, tolerance handling,
sectioning, or a visually approved render. Zero distance and zero intersection
volume can mean face contact or numerical coincidence. Boolean failure and
non-solid inputs report UNKNOWN rather than claiming no interference. The
intersection threshold is 1e-6 mm³; small intersections below that threshold
are not certified absent. SVG output still lacks visual approval.
