# CAD preview verification — 2026-10-05

- Canonical checkout: `E:\design-mcp-server` at `21b41c7`. FreeCAD 1.1.4 bundled Python on D:.
- Existing generic box revision `0575ff07afe34543a097eb3428d73f62` generated preview `2a290b1761d74d9eb9f23ab6addc140f` under `E:\design-mcp-server\.tmp\previews`.
- FreeCAD reported 8 vertices, 12 triangles, 18 unique triangulation edges, and a 640 × 480 SVG canvas. `inspect_cad_preview` verified the source and SVG SHA-256 values and returned `HASH_VERIFIED_NOT_VISUALLY_APPROVED`.
- All 27 unit tests passed on the Windows E: checkout before the live run. This proves export/structure/hash linkage for one generic fixture, **not** adequate appearance, hidden-line removal, sectioning, clearance, or manufacturing validity.
- File-transfer `file.fetch` was denied by its allowlist; no alternate file-transfer route was used. Visual inspection remains a separate pending acceptance step.
