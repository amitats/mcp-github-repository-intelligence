import asyncio
import json

from mcp_integration.client import CompatibilityMCPClient


async def main():
    client = CompatibilityMCPClient()

    result = await client.latest_package(
        "org.springframework.boot:spring-boot",
        "maven",
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())