# FCStd envelope gate — pending (2026-10-05)

At `E:\design-mcp-server` commit `d1b1c42`, all **48** unit tests passed,
including four envelope tests for a separated pair, overlapping and missing
boxes returning UNKNOWN, rejected inputs and changed-source detection.

An E: stdio MCP invocation of `inspect_cad_envelopes` with the four generic
box objects (`First`, `Separated`, `Touching`, `Overlapping`) **timed out** in
the FreeCAD subprocess after its 60-second inspection limit. A subsequent
direct `inspect_freecad` call reopened the same 5,320-byte FCStd and returned
four document objects. A direct envelope replay was denied by Windows node
permissions, so the envelope result is **not live-proven**. Do not claim a
distance result or mark this gate passed until an approved real-file call
returns and its output is checked.

The implemented AABB calculation is conservative: separation gives only a
geometric lower bound. Overlap/missing geometry reports UNKNOWN, never a
physical collision, clearance or component-fit approval. No KiCad CLI was
found on the Windows node PATH; ERC/DRC and neutral STEP exchange are not
provided by this increment.
