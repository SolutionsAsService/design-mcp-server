# Generic project/evidence verification — 2026-10-05

Canonical checkout `E:\design-mcp-server`, commit `5168344`; Python MCP SDK
in its E: virtual environment. The fixture linked an existing generic CAD box
revision and a repository verification note through a fresh snapshot. No
manufacturer data or aircraft design was involved.

- A real stdio client initialized the server, listed **23 tools** and four
  resources, created a snapshot and a typed generic project record, appended
  a source/subject evidence link and inspected the resulting project revision.
- Snapshot status was `CURRENT` (hash agreement only), while the evidence
  relationship was `CONTENT_UNCHANGED_NOT_VERIFIED`; the user-supplied
  evidence status was `UNKNOWN`, and the verification label explicitly read
  `USER_ATTESTED_NOT_INDEPENDENTLY_CHECKED`.
- The client read `design://project/records`. Parent versions and source files
  were not overwritten. All **39 tests** passed on E: before this live run;
  one further changed-CAD-subject regression test was added afterward.

These records have typed source/subject relationships, not a general
dependency graph, manufacturer verification, engineering validation or a
trustworthy signature against malicious replacement. Explicit units are
accepted but not converted. A `VERIFIED` label selected by a caller remains
user-attested; it is not an independent approval.
