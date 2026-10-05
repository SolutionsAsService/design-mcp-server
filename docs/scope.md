# Scope and security

This server is a read-only static asset catalog. It exposes no aircraft/vehicle analysis, component envelopes, dimensions, fit or clearance checks, manufacturing guidance, electrical or propulsion calculations, mass/CG, flight-control, simulation, hardware, or flight-test features.

All tool paths are relative to DESIGN_MCP_ASSET_ROOT. Absolute paths, parent traversal, and symlinks are rejected. The server does not write files, access the network, or launch subprocesses. Inspection has file-size limits.

STRUCTURE_VALID means only that implemented container checks passed; it is not engineering or manufacturing validation. STEP files are hashed without geometry parsing.
