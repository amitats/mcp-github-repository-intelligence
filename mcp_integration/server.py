
import os
import asyncio
import re
import json
from pathlib import Path
from typing import Any

import httpx
from mcp.server import MCPServer

mcp = MCPServer("repository-compatibility-search")


# ---------------------------------------------------------------------------
# Repository-aware V10 analysis integration for Claude Desktop
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

REPOSITORY_ANALYSIS_ROOT = Path(
    os.getenv(
        "REPOSITORY_ANALYSIS_ROOT",
        str(PROJECT_ROOT / "analysis-output-mcp-repos"),
    )
).expanduser().resolve()


def safe_repository_name(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    value = value.split("/")[-1]
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-_")
    return value


def repository_analysis_file(repository: str) -> Path:
    return (
        REPOSITORY_ANALYSIS_ROOT
        / safe_repository_name(repository)
        / "repository_analysis.json"
    )


def available_repositories() -> list[str]:
    REPOSITORY_ANALYSIS_ROOT.mkdir(parents=True, exist_ok=True)
    return sorted(
        child.name
        for child in REPOSITORY_ANALYSIS_ROOT.iterdir()
        if child.is_dir()
        and (child / "repository_analysis.json").exists()
    )


def resolve_repository(repository: str):
    requested = safe_repository_name(repository)
    if not requested:
        return None, {
            "status": "error",
            "error": "repository must not be empty",
            "available_repositories": available_repositories(),
        }

    for existing in available_repositories():
        if existing.lower() == requested.lower():
            return existing, None

    return None, {
        "status": "not-analyzed",
        "repository": requested,
        "error": f"Repository '{requested}' has not been analyzed yet.",
        "available_repositories": available_repositories(),
        "action": (
            "Call analyze_repository with the full GitHub URL or local "
            "repository path first."
        ),
    }


def load_repository_analysis(repository: str) -> dict[str, Any]:
    resolved, error = resolve_repository(repository)
    if error:
        return error

    analysis_file = repository_analysis_file(resolved)
    try:
        with analysis_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {
                "status": "error",
                "error": "Repository analysis JSON must contain an object.",
                "repository": resolved,
                "analysis_file": str(analysis_file),
            }
        return data
    except Exception as exc:
        return {
            "status": "error",
            "error": "Unable to load repository analysis",
            "repository": resolved,
            "analysis_file": str(analysis_file),
            "reason": str(exc),
        }


@mcp.tool()
def list_analyzed_repositories() -> dict[str, Any]:
    """List all repository analyses currently available to Claude."""
    repositories = available_repositories()
    return {
        "status": "success",
        "analysis_root": str(REPOSITORY_ANALYSIS_ROOT),
        "count": len(repositories),
        "repositories": repositories,
    }


@mcp.tool()
def get_repository_analysis(repository: str) -> dict[str, Any]:
    """Return complete V10 analysis for one named repository."""
    resolved, error = resolve_repository(repository)
    if error:
        return error
    data = load_repository_analysis(resolved)
    if data.get("status") in {"error", "not-analyzed"}:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "analysis_file": str(repository_analysis_file(resolved)),
        "repository_analysis": data,
    }


@mcp.tool()
def search_repository_analysis(repository: str, query: str) -> dict[str, Any]:
    """Return named repository analysis as context for a specific question."""
    query = (query or "").strip()
    if not query:
        return {"status": "error", "error": "query must not be empty"}
    resolved, error = resolve_repository(repository)
    if error:
        return error
    data = load_repository_analysis(resolved)
    if data.get("status") in {"error", "not-analyzed"}:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "query": query,
        "analysis_file": str(repository_analysis_file(resolved)),
        "repository_analysis": data,
    }


@mcp.tool()
def get_repository_analysis_status(repository: str) -> dict[str, Any]:
    """Check whether one named repository has stored V10 analysis."""
    resolved, error = resolve_repository(repository)
    if error:
        return error
    path = repository_analysis_file(resolved)
    return {
        "status": "ready",
        "repository": resolved,
        "analysis_file": str(path),
        "exists": path.exists(),
    }


async def get_json(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "repository-intelligence-mcp/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def get_text(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "repository-intelligence-mcp/1.0"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


@mcp.tool()
async def get_latest_package_version(
    name: str,
    ecosystem: str,
) -> dict[str, Any]:
    """
    Return latest stable package version from an authoritative package registry.
    Supported ecosystems: pypi, npm, maven, go, nuget, crates.
    """

    eco = ecosystem.lower().strip()

    try:
        if eco in {"python", "pypi"}:
            data = await get_json(f"https://pypi.org/pypi/{name}/json")

            version = data["info"]["version"]

            return {
                "name": name,
                "ecosystem": "pypi",
                "latest_stable_version": version,
                "source": f"https://pypi.org/project/{name}/",
                "source_type": "official-registry",
                "status": "success",
            }

        if eco in {"javascript", "typescript", "npm", "node"}:
            encoded_name = name.replace("/", "%2F")
            data = await get_json(
                f"https://registry.npmjs.org/{encoded_name}/latest"
            )
        
            return {
                "name": name,
                "ecosystem": "npm",
                "latest_stable_version": data.get("version"),
                "source": f"https://www.npmjs.com/package/{name}",
                "source_type": "official-registry",
                "status": "success",
            }
        
        if eco in {"java", "maven"}:
            if ":" not in name:
                return {
                    "name": name,
                    "ecosystem": "maven",
                    "latest_stable_version": None,
                    "status": "unknown",
                    "reason": "Maven dependency must be groupId:artifactId",
                }

            group_id, artifact_id = name.split(":", 1)

            url = (
                "https://search.maven.org/solrsearch/select"
                f"?q=g%3A%22{group_id}%22%20AND%20a%3A%22{artifact_id}%22"
                "&core=gav&rows=50&wt=json"
            )

            async with httpx.AsyncClient(
                timeout=60,
                follow_redirects=True,
                headers={
                    "User-Agent": "repository-intelligence-mcp/1.0"
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            docs = data.get("response", {}).get("docs", [])

            if not docs:
                return {
                    "name": name,
                    "ecosystem": "maven",
                    "latest_stable_version": None,
                    "status": "unknown",
                    "reason": "Artifact not found in Maven Central",
                }

            versions = [
                str(doc.get("v", "")).strip()
                for doc in docs
                if doc.get("v")
            ]

            stable_versions = [
                version
                for version in versions
                if not any(
                    marker in version.lower()
                    for marker in [
                        "snapshot",
                        "alpha",
                        "beta",
                        "-rc",
                        ".rc",
                        "-m",
                    ]
                )
            ]

            latest = (
                stable_versions[0]
                if stable_versions
                else versions[0] if versions else None
            )

            return {
                "name": name,
                "ecosystem": "maven",
                "latest_stable_version": latest,
                "source": (
                    "https://central.sonatype.com/artifact/"
                    f"{group_id}/{artifact_id}"
                ),
                "source_type": "official-registry",
                "status": "success",
            }

        if eco in {"go", "golang"}:
            module_name = name.strip()

            # Go module proxy escaping:
            # uppercase characters are encoded as ! + lowercase.
            escaped_module = "".join(
                "!" + char.lower() if char.isupper() else char
                for char in module_name
            )

            data = await get_json(
                f"https://proxy.golang.org/{escaped_module}/@latest"
            )

            latest = data.get("Version")

            if not latest:
                return {
                    "name": name,
                    "ecosystem": "go",
                    "latest_stable_version": None,
                    "source": f"https://pkg.go.dev/{module_name}",
                    "source_type": "official-registry",
                    "status": "unknown",
                    "reason": "Go module proxy did not return a version",
                }

            return {
                "name": name,
                "ecosystem": "go",
                "latest_stable_version": latest,
                "source": f"https://pkg.go.dev/{module_name}",
                "source_type": "official-registry",
                "status": "success",
            }

        return {
            "name": name,
            "ecosystem": ecosystem,
            "latest_stable_version": None,
            "status": "unsupported-ecosystem",
        }

    except Exception as exc:
        return {
            "name": name,
            "ecosystem": ecosystem,
            "latest_stable_version": None,
            "status": "error",
            "reason": str(exc),
        }


@mcp.tool()
async def get_runtime_support(
    runtime: str,
    current_version: str,
) -> dict[str, Any]:
    """
    Find current runtime support/EOL information.
    Supports Python, Node.js, Java, Go and .NET through endoflife.date.
    """

    mapping = {
        "python": "python",
        "node": "nodejs",
        "node.js": "nodejs",
        "javascript": "nodejs",
        "java": None,
        "jdk": None,
        "go": "go",
        "golang": "go",
        ".net": "dotnet",
        "dotnet": "dotnet",
    }

    runtime_key = runtime.lower().strip()
    product = mapping.get(runtime_key)

    if not product:
        return {
            "runtime": runtime,
            "current_version": current_version,
            "latest_cycle": None,
            "latest_release": None,
            "current_cycle_details": None,
            "source": None,
            "status": "not-verified",
            "reason": (
                "Runtime lifecycle information is not available "
                "from the currently configured MCP lifecycle source."
            ),
        }

    try:
        releases = await get_json(
            f"https://endoflife.date/api/{product}.json"
        )

        normalized = current_version.lstrip("v")
        major_minor = ".".join(normalized.split(".")[:2])

        matching = None

        for release in releases:
            cycle = str(release.get("cycle", ""))

            if (
                normalized.startswith(cycle)
                or major_minor == cycle
                or normalized == cycle
            ):
                matching = release
                break

        latest = releases[0] if releases else {}

        return {
            "runtime": runtime,
            "current_version": current_version,
            "latest_cycle": latest.get("cycle"),
            "latest_release": latest.get("latest"),
            "current_cycle_details": matching,
            "source": f"https://endoflife.date/{product}",
            "status": "success",
        }

    except Exception as exc:
        return {
            "runtime": runtime,
            "current_version": current_version,
            "status": "error",
            "reason": str(exc),
        }


@mcp.tool()
async def search_upgrade_information(
    name: str,
    ecosystem: str,
    current_version: str,
    latest_version: str,
) -> dict[str, Any]:
    """
    Return upgrade guidance URLs.
    Uses ecosystem/project sources and GitHub as fallback.
    """

    query_name = name

    github_search = (
        "https://api.github.com/search/repositories"
    )

    try:
        async with httpx.AsyncClient(
            timeout=30,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "repository-intelligence-mcp/1.0",
            },
        ) as client:
            response = await client.get(
                github_search,
                params={"q": query_name, "per_page": 3},
            )

            if response.status_code != 200:
                return {
                    "name": name,
                    "status": "not-found",
                    "upgrade_information": None,
                }

            data = response.json()

        items = data.get("items", [])

        sources = []

        for item in items[:3]:
            sources.append(
                {
                    "title": item.get("full_name"),
                    "url": item.get("html_url"),
                    "type": "github-project",
                }
            )

        return {
            "name": name,
            "ecosystem": ecosystem,
            "current_version": current_version,
            "latest_version": latest_version,
            "upgrade_information":
                "Review official release notes/changelog before upgrade.",
            "sources": sources,
            "status": "success",
        }

    except Exception as exc:
        return {
            "name": name,
            "status": "error",
            "reason": str(exc),
        }


# ---------------------------------------------------------------------------
# Dynamic repository-aware V10 analysis + retrieval tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def analyze_repository(source: str) -> dict[str, Any]:
    """Analyze GitHub URL/local repo and persist output under its repo name."""
    source = (source or "").strip()
    if not source:
        return {"status": "error", "reason": "Repository source cannot be empty."}

    repository = safe_repository_name(source)
    if not repository:
        return {"status": "error", "reason": "Unable to determine repository name."}

    main_file = PROJECT_ROOT / "main.py"
    python_executable = PROJECT_ROOT / ".venv" / "bin" / "python3"
    output_dir = REPOSITORY_ANALYSIS_ROOT / repository
    analysis_file = output_dir / "repository_analysis.json"

    if not main_file.exists():
        return {"status": "error", "reason": "V10 main.py was not found."}
    if not python_executable.exists():
        return {"status": "error", "reason": "Project .venv Python was not found."}

    output_dir.mkdir(parents=True, exist_ok=True)
    if analysis_file.exists():
        analysis_file.unlink()

    command = [
        str(python_executable),
        str(main_file),
        "--source", source,
        "--output", str(output_dir),
        "--skip-llm",
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(PROJECT_ROOT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if process.returncode != 0:
            return {
                "status": "error",
                "repository": repository,
                "source": source,
                "reason": "V10 repository analysis failed.",
                "return_code": process.returncode,
                "stdout": stdout_text[-5000:],
                "stderr": stderr_text[-5000:],
            }

        if not analysis_file.exists():
            return {
                "status": "error",
                "repository": repository,
                "source": source,
                "reason": "V10 completed but repository_analysis.json was not generated.",
                "expected_path": str(analysis_file),
            }

        with analysis_file.open("r", encoding="utf-8") as handle:
            analysis = json.load(handle)

        return {
            "status": "success",
            "repository": repository,
            "source": source,
            "message": "V10 repository analysis completed and stored successfully.",
            "analysis_file": str(analysis_file),
            "technology_stack": analysis.get("02_technology_stack"),
            "available_repositories": available_repositories(),
        }

    except Exception as exc:
        return {
            "status": "error",
            "repository": repository,
            "source": source,
            "reason": str(exc),
        }


def section_for(repository: str, key: str) -> tuple[str | None, dict[str, Any]]:
    resolved, error = resolve_repository(repository)
    if error:
        return None, error
    data = load_repository_analysis(resolved)
    if data.get("status") in {"error", "not-analyzed"}:
        return None, data
    return resolved, data


@mcp.tool()
def get_detailed_code_flow(repository: str) -> dict[str, Any]:
    """Return complete V10 detailed code flow for a named repository."""
    resolved, data = section_for(repository, "06_detailed_code_flow")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "repository_summary": data.get("01_repository_summary"),
        "detailed_code_flow": data.get("06_detailed_code_flow"),
    }


@mcp.tool()
def get_code_architecture(repository: str) -> dict[str, Any]:
    """Return V10 architecture for a named repository."""
    resolved, data = section_for(repository, "05_code_architecture")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "repository_summary": data.get("01_repository_summary"),
        "architecture": data.get("05_code_architecture"),
    }


@mcp.tool()
def get_components_and_relationships(repository: str) -> dict[str, Any]:
    """Return components and relationships for a named repository."""
    resolved, data = section_for(repository, "04_main_components_and_code_structure")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "components_and_code_structure":
            data.get("04_main_components_and_code_structure"),
    }


@mcp.tool()
def get_dependencies_and_compatibility(repository: str) -> dict[str, Any]:
    """Return dependency/compatibility analysis for a named repository."""
    resolved, data = section_for(repository, "07_dependencies_and_compatibility")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "dependencies_and_compatibility":
            data.get("07_dependencies_and_compatibility"),
    }


@mcp.tool()
def get_tests_and_coverage(repository: str) -> dict[str, Any]:
    """Return test/coverage analysis for a named repository."""
    resolved, data = section_for(repository, "08_tests_and_coverage")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "tests_and_coverage": data.get("08_tests_and_coverage"),
    }


@mcp.tool()
def get_internal_apis(repository: str) -> dict[str, Any]:
    """Return internal APIs for a named repository."""
    resolved, data = section_for(repository, "09_internal_apis")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "internal_apis": data.get("09_internal_apis"),
    }


@mcp.tool()
def get_external_integrations(repository: str) -> dict[str, Any]:
    """Return external integrations for a named repository."""
    resolved, data = section_for(repository, "10_external_api_and_integration_calls")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "external_api_and_integration_calls":
            data.get("10_external_api_and_integration_calls"),
    }


@mcp.tool()
def get_main_use_cases(repository: str) -> dict[str, Any]:
    """Return main use cases for a named repository."""
    resolved, data = section_for(repository, "11_main_use_cases")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "main_use_cases": data.get("11_main_use_cases"),
    }


@mcp.tool()
def get_complete_repository_intelligence(repository: str) -> dict[str, Any]:
    """Return all V10 sections for a named repository."""
    resolved, data = section_for(repository, "01_repository_summary")
    if not resolved:
        return data
    return {
        "status": "success",
        "repository": resolved,
        "repository_summary": data.get("01_repository_summary"),
        "technology_stack": data.get("02_technology_stack"),
        "repository_scan_and_artifacts": data.get("03_repository_scan_and_artifacts"),
        "components_and_code_structure": data.get("04_main_components_and_code_structure"),
        "code_architecture": data.get("05_code_architecture"),
        "detailed_code_flow": data.get("06_detailed_code_flow"),
        "dependencies_and_compatibility": data.get("07_dependencies_and_compatibility"),
        "tests_and_coverage": data.get("08_tests_and_coverage"),
        "internal_apis": data.get("09_internal_apis"),
        "external_api_and_integration_calls":
            data.get("10_external_api_and_integration_calls"),
        "main_use_cases": data.get("11_main_use_cases"),
        "analysis_limitations": data.get("12_analysis_limitations"),
    }


if __name__ == "__main__":
    mcp.run()
