# KiCad, pcbparts and design-MCP coordination

The MCP services are separate. `design-mcp-server` has no authenticated
server-to-server connection and does not fetch parts or mutate a KiCad board.
An agent explicitly passes observed, bounded data between tools. The stored
record hash covers the forwarded payload, **not** its authenticity.

## Observed surfaces (2026-10-05)

- `pcbparts.jlc_search` and `pcbparts.jlc_get_part` returned catalog data for
  `C25804` / `0603WAF1002T5E` (UNI-ROYAL) as a read-only generic fixture.
  Stock and price are observations, not live order commitments.
- `kicad.library.search` returned
  `Resistor_SMD:R_0603_1608Metric` with two pads. A separate
  `kicad.pcb.get_footprint_dimensions` call failed with a character-encoding
  error, so footprint dimensions and pin/pad mapping remain unverified.
- `kicad-cli` was not found on the Windows node PATH. A separately exposed
  KiCad MCP does not prove the server can invoke KiCad locally or export STEP.

## Guarded handoff

1. Query pcbparts for a specific part and KiCad library search for a footprint
   without ordering or editing anything. Forward the selected output or a
   clearly identified subset; retain the tool name and observation time
   outside conversation as needed. A subset is not a complete source record.
2. Pass the selected `jlc_get_part` result and one KiCad footprint-search result
   to `register_component_candidate`. It stores the forwarded packets and
   normalized identifiers under the opt-in revision root. Inspect the record
   before using it. Status remains `UNVERIFIED_CANDIDATE_NOT_PIN_OR_PACKAGE_CHECKED`.
3. `create_assembly_manifest` may reference candidate IDs at user-supplied
   positions and parent references. It verifies their saved hashes and checks
   hierarchy cycles/duplicates. `inspect_assembly_manifest` reports
   `UNKNOWN_MISSING_SOURCE_BACKED_ENVELOPES`, never component fit.
4. To advance: obtain authoritative manufacturer dimensions/mounting drawings
   or exact CAD with version/page provenance; prove KiCad footprint/pad mapping;
   link an exported PCB model to the source board hash; inspect geometry in
   FreeCAD; use tolerance-aware clearances only after those inputs are checked.
5. Run KiCad ERC/DRC through a verified adapter and capture project/board hashes,
   CLI version and reports before linking the PCB into a mechanical assembly.
   If an adapter is unavailable, report `CONFIGURATION_REQUIRED`, not PASS.

## Next implementation gates

- Define a sourced component envelope record (dimensions, keepouts, mounting,
  units, document locator/revision, CAD-model hash) and return UNKNOWN for
  missing or merely caller-transcribed measurements.
- Import real KiCad PCB/footprint geometry through a version-tested read-only
  route; retain source project hash and distinguish footprint copper bounds
  from the physical body outline.
- Add explicit instance-to-CAD placement links and bounded spatial checks,
  preserving UNKNOWN for missing envelopes, unknown orientation or tolerance.
- Keep one mutating PCB toolchain at a time. No purchases, arbitrary board
  writes, flight integration or physical actuation follow from these records.
