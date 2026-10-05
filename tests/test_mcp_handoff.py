"""Exercise the stdio handoff using observed, unverified part identifiers."""

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    ClientSession = None


@unittest.skipIf(ClientSession is None, "MCP SDK is not installed")
class McpHandoffTests(unittest.TestCase):
    def test_candidate_assembly_and_resource(self) -> None:
        async def run(output_root: str) -> None:
            project_root = str(Path(__file__).resolve().parent.parent)
            environment = dict(os.environ, DESIGN_MCP_ASSET_ROOT=project_root,
                               DESIGN_MCP_REVISION_ROOT=output_root)
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "design_mcp.server"],
                                               env=environment, cwd=project_root)
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    self.assertIn("register_component_candidate", {tool.name for tool in tools.tools})

                    async def call(name: str, arguments: dict) -> dict:
                        result = await session.call_tool(name, arguments)
                        self.assertFalse(result.isError, result.content)
                        return json.loads(result.content[0].text)

                    candidate = await call("register_component_candidate", {
                        "part_output": {"lcsc": "C25804", "model": "0603WAF1002T5E",
                                        "manufacturer": "UNI-ROYAL(Uniroyal Elec)"},
                        "footprint_output": {"library": "Resistor_SMD", "name": "R_0603_1608Metric",
                                             "full_name": "Resistor_SMD:R_0603_1608Metric", "pad_count": 2},
                    })
                    assembly = await call("create_assembly_manifest", {
                        "name": "Generic fixture", "instances": [
                            {"reference": "R1", "candidate_id": candidate["candidate_id"],
                             "position_mm": [0, 0, 0]}],
                    })
                    report = await call("inspect_assembly_manifest", {"assembly_id": assembly["assembly_id"]})
                    self.assertEqual(report["reference_status"], "HASHES_CURRENT")
                    self.assertEqual(report["fit_status"], "UNKNOWN_MISSING_SOURCE_BACKED_ENVELOPES")
                    resource = await session.read_resource("design://components/candidates")
                    self.assertTrue(resource.contents)

        with tempfile.TemporaryDirectory() as output_root:
            asyncio.run(run(output_root))


if __name__ == "__main__":
    unittest.main()
