import asyncio

from mcp_integration.compatibility_enricher import enrich_dependencies


def mark_skipped(groups):
    """
    Mark dependency compatibility as skipped.
    Static dependency/version information remains unchanged.
    """
    for deps in groups.values():
        for d in deps:
            d.compatibility_status = "Not checked - MCP/Search skipped"
            d.compatibility_notes = (
                "Current version/constraint extracted locally. "
                "Latest compatibility was not checked."
            )

    return groups


async def _enrich_async(groups):
    """
    Enrich production/runtime dependencies using the MCP compatibility service.
    """

    for scope, deps in groups.items():

        # Do not spend external lookups on non-production dependencies.
        if scope in {
            "example",
            "test",
            "documentation",
            "development",
        }:
            for d in deps:
                d.compatibility_status = "Not checked - non-core dependency"
            continue

        # Convert V10 Dependency objects into the format expected
        # by compatibility_enricher.py.
        dependency_input = []

        for d in deps:
            dependency_input.append(
                {
                    "name": d.name,
                    "current_version": d.current_version,
                    "source": d.source_file,
                }
            )

        if not dependency_input:
            continue

        try:
            results = await enrich_dependencies(dependency_input)

        except Exception as exc:
            for d in deps:
                d.compatibility_status = "Unable to determine"
                d.compatibility_notes = (
                    f"MCP compatibility lookup failed: "
                    f"{type(exc).__name__}: {exc}"
                )
            continue

        # Map MCP results back to the existing V10 Dependency objects.
        for d, result in zip(deps, results):

            d.latest_version = (
                result.get("latest_version") or ""
            )

            d.compatibility_status = (
                result.get("compatibility")
                or result.get("compatibility_status")
                or "Unable to determine"
            )

            notes = []

            if result.get("recommendation"):
                notes.append(str(result["recommendation"]))

            if result.get("upgrade_information"):
                upgrade = result["upgrade_information"]

                if isinstance(upgrade, dict):
                    if upgrade.get("summary"):
                        notes.append(str(upgrade["summary"]))
                    elif upgrade.get("recommendation"):
                        notes.append(
                            str(upgrade["recommendation"])
                        )
                elif upgrade:
                    notes.append(str(upgrade))

            source = (
                result.get("latest_version_source")
                or result.get("source")
            )

            if source:
                notes.append(f"Latest version source: {source}")

            if result.get("reason"):
                notes.append(str(result["reason"]))

            d.compatibility_notes = (
                " | ".join(notes)
                if notes
                else "Compatibility checked through MCP."
            )

    return groups


def enrich(groups, runtimes):
    """
    Synchronous V10 entry point.

    main.py already calls this function, therefore no main.py
    modification is required.
    """

    try:
        return asyncio.run(_enrich_async(groups))

    except Exception as exc:

        for deps in groups.values():
            for d in deps:
                if not d.compatibility_status or d.compatibility_status == "Not checked":
                    d.compatibility_status = "Unable to determine"
                    d.compatibility_notes = (
                        f"MCP integration failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

        return groups
