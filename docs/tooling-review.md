# Existing tooling review

Read-only web review completed 2026-10-04:

- mattmohandiss/cad-mcp-server advertises local read-only STEP geometry inspection, measurement, revision comparison, and DFM checks. Its README states MIT licensing and a bundled LGPL-2.1 Open CASCADE kernel.
- Repository: https://github.com/mattmohandiss/cad-mcp-server
- It was not cloned, installed, or security-audited. Its geometry measurement and DFM surface is broader than this catalog's fixed scope.
- This project therefore implements only file inventory, hashing, and basic container integrity. It does not parse STEP geometry or integrate FreeCAD.
