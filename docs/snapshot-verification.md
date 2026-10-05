# Generic snapshot verification — 2026-10-05

Canonical checkout `E:\design-mcp-server`, commit `1cbfa35`; Python MCP SDK in its
E: virtual environment. The dedicated revision directory held an earlier
generated generic FreeCAD box; no vehicle project data was used.

- `create_project_snapshot` linked one read-only asset (`README.md`) and one
  hash-checked generated-box revision into an immutable snapshot manifest.
- `inspect_project_snapshot` returned `CURRENT` for both content references;
  `list_project_snapshots` returned one manifest summary in this test directory.
- A real stdio MCP client initialized the server, listed **19 tools** and the
  three `design://project/assets`, `design://project/revisions`, and
  `design://project/snapshots` resources, called `inspect_project_snapshot`
  without a tool error and read the snapshots resource.
- All **35 tests** passed on the E: checkout, including unit tests for changed
  assets/revision models, missing files, invalid manifests, traversal and
  oversized/unknown references.

`CURRENT` establishes only content-hash agreement at inspection time, not
geometry accuracy, engineering compatibility, or an approved build. The
manifest hash detects accidental alteration inside a trusted revision root;
it is not a signature against malicious replacement. Snapshot IDs do not yet
form a typed project, dependency graph or automatic change propagation.
