import os
import sys
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SERVER_FILE = (
    PROJECT_ROOT
    / "mcp_integration"
    / "server.py"
)


class CompatibilityMCPClient:

    async def _call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_FILE)],
            env={
                "PATH": os.environ.get("PATH", ""),
                "HOME": os.environ.get("HOME", ""),
            },
        )

        transport = stdio_client(server_params)

        async with Client(transport) as client:

            result = await client.call_tool(
                tool_name,
                arguments,
            )

            if result.is_error:
                return {
                    "status": "error",
                    "reason": "MCP tool returned error",
                }

            if result.structured_content:
                return result.structured_content

            return {
                "status": "error",
                "reason":
                    "No structured result returned by MCP",
            }

    async def latest_package(
        self,
        name: str,
        ecosystem: str,
    ) -> dict[str, Any]:

        return await self._call(
            "get_latest_package_version",
            {
                "name": name,
                "ecosystem": ecosystem,
            },
        )

    async def runtime_support(
        self,
        runtime: str,
        current_version: str,
    ) -> dict[str, Any]:

        return await self._call(
            "get_runtime_support",
            {
                "runtime": runtime,
                "current_version": current_version,
            },
        )

    async def upgrade_information(
        self,
        name: str,
        ecosystem: str,
        current_version: str,
        latest_version: str,
    ) -> dict[str, Any]:

        return await self._call(
            "search_upgrade_information",
            {
                "name": name,
                "ecosystem": ecosystem,
                "current_version": current_version,
                "latest_version": latest_version,
            },
        )