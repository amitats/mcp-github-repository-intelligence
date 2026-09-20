import asyncio
import json

from mcp_integration.compatibility_enricher import enrich_dependencies


async def main():
    dependencies = [
        {
            "name": "github.com/gin-gonic/gin",
            "current_version": "v1.10.0",
            "source": "go.mod",
        },
        {
            "name": "requests",
            "current_version": "2.31.0",
            "source": "requirements.txt",
        },
        {
            "name": "express",
            "current_version": "4.18.2",
            "source": "package.json",
        },
        {
            "name": "org.springframework.boot:spring-boot",
            "current_version": "3.3.0",
            "source": "pom.xml",
        },
    ]

    results = await enrich_dependencies(dependencies)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())