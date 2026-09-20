"""Deterministic helpers for the Overall Code Flow section.

The local LLM may explain the flow, but it is not allowed to invent the flow.
This module converts static facts into a usable fallback and into compact
repository evidence for a dedicated code-flow LLM pass.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any


def _clean(value: Any) -> str:
    return str(value or "").strip()


def classify_entry_point(entry: dict[str, Any]) -> str:
    source = _clean(entry.get("source_file")).lower()
    typ = _clean(entry.get("type")).lower()
    symbol = _clean(entry.get("symbol")).lower()
    joined = f"{source} {typ} {symbol}"
    if ".github/workflows/" in joined:
        return "CI/CD workflow"
    if ".github/scripts/" in joined:
        return "Repository automation/reporting"
    if any(x in joined for x in ("/scripts/", "scripts/", "/tools/", "tools/")):
        return "Operational/tooling script"
    if "npm script" in typ or "executable entry point" in typ or ":main" in symbol:
        return "Application/runtime entry point"
    if "package" in typ or "module" in typ:
        return "Package/library entry point"
    return "Detected entry point"


def grouped_entry_points(facts) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ep in facts.architecture_facts.entry_points:
        groups[classify_entry_point(ep)].append(ep)
    return dict(groups)


def _relationship_summary(facts, limit: int = 20) -> list[str]:
    out = []
    for r in facts.architecture_facts.component_relationships[:limit]:
        src = _clean(r.get("from"))
        dst = _clean(r.get("to"))
        rel = _clean(r.get("relationship")) or "depends on"
        if src and dst and src != dst:
            out.append(f"{src} -> {dst} ({rel})")
    return out


def _flow_summary(facts, limit: int = 10) -> list[dict[str, Any]]:
    out = []
    for f in facts.architecture_facts.detailed_code_flows[:limit]:
        steps = [_clean(x) for x in f.get("steps", []) if _clean(x)]
        if not steps:
            continue
        out.append({
            "name": _clean(f.get("name")),
            "entry_point": _clean(f.get("entry_point")),
            "steps": steps[:12],
            "evidence": [_clean(x) for x in f.get("evidence", []) if _clean(x)][:5],
        })
    return out


def code_flow_evidence(facts) -> dict[str, Any]:
    """Small, factual structure designed for the dedicated code-flow prompt."""
    return {
        "repository_name": facts.repository_name,
        "repository_kind": facts.repository_kind,
        "project_description": facts.project_description,
        "readme_summary": facts.readme_summary,
        "technology_stack": facts.technology_stack,
        "entry_points_by_type": grouped_entry_points(facts),
        "major_components": facts.architecture_facts.major_components[:20],
        "component_relationships": _relationship_summary(facts, 30),
        "configuration_model": facts.architecture_facts.configuration_model,
        "deployment_model": facts.architecture_facts.deployment_model,
        "static_detailed_flows": _flow_summary(facts, 12),
        "internal_apis": [asdict(x) for x in facts.internal_apis[:30]],
        "external_calls": [asdict(x) for x in facts.external_calls[:30]],
        "configuration_files": facts.artifacts.get("configuration", [])[:20],
        "ci_cd_files": facts.artifacts.get("ci_cd", [])[:30],
        "documentation_files": facts.artifacts.get("documentation", [])[:15],
        "architecture_evidence": facts.architecture_facts.evidence[:10],
    }


def static_overall_code_flow(facts) -> list[dict[str, Any]]:
    """Detailed deterministic fallback when the local LLM is unavailable.

    It intentionally describes only facts that are already present in static
    analysis. It does not pretend to know business behavior that was not proven.
    """
    arch = facts.architecture_facts
    groups = grouped_entry_points(facts)
    steps: list[dict[str, Any]] = []

    runtime_eps = groups.get("Application/runtime entry point", [])
    automation_eps = groups.get("Repository automation/reporting", [])
    tooling_eps = groups.get("Operational/tooling script", [])
    package_eps = groups.get("Package/library entry point", [])

    if runtime_eps:
        files = [x.get("source_file", "") for x in runtime_eps[:8] if x.get("source_file")]
        steps.append({
            "step": 1,
            "title": "Start from the runtime entry point",
            "explanation": "The main runtime flow starts from the executable entry points detected in the repository. These files or commands initialize the executable path before work is delegated to repository modules.",
            "code": files,
            "result": "Runtime execution is initialized and control moves into application modules.",
            "evidence": ["Static executable/package entry-point detection"],
        })
    elif package_eps:
        files = [x.get("source_file", "") for x in package_eps[:8] if x.get("source_file")]
        steps.append({
            "step": 1,
            "title": "Enter through the package/library interface",
            "explanation": "No single application runtime entry point was proven. The repository exposes package or library entry points, so execution begins when another program imports or invokes those interfaces.",
            "code": files,
            "result": "Control enters the reusable package/module implementation.",
            "evidence": ["Static package entry-point detection"],
        })
    else:
        files = [x.get("source_file", "") for x in (automation_eps + tooling_eps)[:8] if x.get("source_file")]
        steps.append({
            "step": 1,
            "title": "Start from one of the repository scripts or automation paths",
            "explanation": "The repository has multiple independent executable scripts rather than one proven application entry point. Each script starts its own workflow and then calls the functions/modules needed for that task.",
            "code": files,
            "result": "The selected script begins its task-specific workflow.",
            "evidence": ["Static script entry-point detection"],
        })

    config_files = facts.artifacts.get("configuration", [])[:12]
    if config_files:
        steps.append({
            "step": len(steps)+1,
            "title": "Read repository configuration",
            "explanation": "Configuration files provide values that influence how the repository scripts/components run. Static analysis confirms these configuration artifacts exist; individual runtime values are not guessed when they cannot be resolved from code.",
            "code": config_files,
            "result": "The workflow has the configuration needed for later processing.",
            "evidence": [arch.configuration_model],
        })

    # Use proven callable/import flows as the middle of the explanation.
    for flow in arch.detailed_code_flows[:6]:
        call_steps = [_clean(x) for x in flow.get("steps", []) if _clean(x)]
        if len(call_steps) < 2:
            continue
        steps.append({
            "step": len(steps)+1,
            "title": _clean(flow.get("name")) or "Execute repository processing flow",
            "explanation": "The code follows this statically proven sequence of local calls/modules: " + " -> ".join(call_steps) + ".",
            "code": call_steps,
            "result": "Control continues to the next local processing function/module or returns to its caller.",
            "evidence": [_clean(x) for x in flow.get("evidence", []) if _clean(x)] or ["Static call/import analysis"],
        })

    rels = _relationship_summary(facts, 12)
    if rels:
        steps.append({
            "step": len(steps)+1,
            "title": "Delegate work between repository modules",
            "explanation": "Repository modules pass control through the local dependency/import relationships detected by static analysis. This shows how implementation areas are connected without relying on LLM assumptions.",
            "code": rels,
            "result": "Processing moves through the required internal modules/components.",
            "evidence": [f"{len(arch.component_relationships)} repository-local relationship(s) detected"],
        })

    if facts.internal_apis:
        endpoints = [f"{x.method} {x.endpoint} -> {x.handler}" for x in facts.internal_apis[:12]]
        steps.append({
            "step": len(steps)+1,
            "title": "Handle internal API requests",
            "explanation": "Where the repository exposes production API routes, requests enter through the detected route and handler before being delegated to repository processing logic.",
            "code": endpoints,
            "result": "The API handler receives the request and passes it into application logic.",
            "evidence": [x.source_file for x in facts.internal_apis[:8]],
        })

    if facts.external_calls:
        calls = []
        for x in facts.external_calls[:12]:
            target = x.target or "target resolved at runtime"
            calls.append(f"{x.caller}: {x.method} {target} via {x.technology} ({x.source_file})")
        steps.append({
            "step": len(steps)+1,
            "title": "Call external systems where required",
            "explanation": "Production code performs the statically detected outbound calls. The report shows the caller, method, technology and target when that target can be resolved from repository evidence.",
            "code": calls,
            "result": "External data/action is requested and the result returns to the calling repository component.",
            "evidence": [x.evidence for x in facts.external_calls[:8] if x.evidence],
        })

    if automation_eps:
        steps.append({
            "step": len(steps)+1,
            "title": "Run repository automation/reporting flows separately",
            "explanation": "Repository automation scripts are separate executable paths from the main runtime flow. They perform repository/reporting/operational tasks and should not be confused with the core application runtime.",
            "code": [x.get("source_file", "") for x in automation_eps[:10]],
            "result": "Automation/reporting tasks complete independently of the main runtime path.",
            "evidence": ["Entry points classified by source location"],
        })

    if tooling_eps:
        steps.append({
            "step": len(steps)+1,
            "title": "Run operational tools when explicitly invoked",
            "explanation": "Operational scripts form additional independent flows. They start only when invoked and use repository modules for their specific task.",
            "code": [x.get("source_file", "") for x in tooling_eps[:10]],
            "result": "The requested operational task finishes and returns its result/output.",
            "evidence": ["Static script entry-point classification"],
        })

    steps.append({
        "step": len(steps)+1,
        "title": "Return or produce the workflow result",
        "explanation": "After local processing and any required integrations finish, control returns to the calling entry point. The exact output is reported only when it is proven by the source; otherwise the analyzer does not invent a file, response, database write or message destination.",
        "code": [],
        "result": "The selected repository workflow completes.",
        "evidence": ["Conservative static-analysis fallback"],
    })

    # Keep output readable while still detailed.
    return steps[:16]
