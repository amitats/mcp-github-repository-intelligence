import asyncio
import json

from mcp_integration.compatibility_enricher import enrich_runtime


async def main():
    tests = [
        ("python", "3.11"),
        ("node", "20"),
        ("java", "17"),
        ("go", "1.23"),
        ("dotnet", "8"),
    ]

    for runtime, version in tests:
        print(f"\n=== {runtime} {version} ===")

        result = await enrich_runtime(runtime, version)

        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
