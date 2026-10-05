# Generic project quantity verification — 2026-10-05

Canonical checkout `E:\design-mcp-server` at `1402ff1`. The live stdio MCP
client listed **26 tools** and used a previously created generic project
record linked to a hash-checked fixture note and box revision.

- `add_project_requirement` created an immutable v2 child with a user-proposed
  `EQUAL` generic width requirement of 3 mm, canonicalized to 0.003 m.
- `add_project_parameter` created another immutable child with a source-linked
  generic nominal width of 0.003 m. Both retained their parent records.
- `convert_quantity(3, "mm", "m")` returned 0.003 m. Unit tests also cover mass,
  area and volume conversion, incompatible dimensions and non-finite values.
- `inspect_project_record` reported a `CURRENT` snapshot. The evidence link
  remained `CONTENT_UNCHANGED_NOT_VERIFIED` and the two quantities were
  `CONTENT_UNCHANGED_NOT_VALIDATED`.
- All **44** tests passed locally and on the E: checkout.

`CURRENT` means hashes still match, not that a requirement is satisfied.
No comparisons to measured values, automatic CAD regeneration, independent
evidence verification, general dimensional algebra or engineering approval
were implemented. Input quantities remain user-proposed.
