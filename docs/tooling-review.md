# Existing tooling review

Read-only web review completed 2026-10-04:

- mattmohandiss/cad-mcp-server advertises local read-only STEP geometry inspection, measurement, revision comparison, and DFM checks. Its README states MIT licensing and a bundled LGPL-2.1 Open CASCADE kernel.
- Repository: https://github.com/mattmohandiss/cad-mcp-server
- It was not cloned, installed, or security-audited. Its geometry measurement and DFM surface is broader than this catalog's fixed scope.
- At the time of this review, this project implemented only inventory and container checks. Since then, native FreeCAD inspection has been added using a verified 1.1.4 runtime on D:, along with STL geometry reasoning and an opt-in generic revision writer. No third-party CAD MCP was installed by this project; read `capability-audit.md` for the current implementation and verification gaps.
