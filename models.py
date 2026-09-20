from dataclasses import dataclass, field
from typing import Any

@dataclass
class Dependency:
    name: str
    current_version: str = ""
    scope: str = "core"
    source_file: str = ""
    latest_version: str = ""
    compatibility_status: str = "Not checked"
    compatibility_notes: str = ""

@dataclass
class ApiEndpoint:
    method: str
    endpoint: str
    handler: str
    component: str
    source_file: str

@dataclass
class ExternalCall:
    caller: str
    technology: str
    target: str
    method: str
    source_file: str
    evidence: str = ""

@dataclass
class TestAnalysis:
    frameworks: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    test_categories: list[str] = field(default_factory=list)
    coverage_percentage: float | None = None
    coverage_source: str = ""
    coverage_status: str = "Actual coverage result not found"

@dataclass
class ArchitectureFacts:
    architecture_style: str = ""
    architecture_explanation: str = ""
    layers_modules: list[dict[str, Any]] = field(default_factory=list)
    entry_points: list[dict[str, Any]] = field(default_factory=list)
    major_components: list[dict[str, Any]] = field(default_factory=list)
    component_relationships: list[dict[str, Any]] = field(default_factory=list)
    configuration_model: str = ""
    extension_points: list[str] = field(default_factory=list)
    deployment_model: str = ""
    data_control_flow: list[str] = field(default_factory=list)
    detailed_code_flows: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

@dataclass
class RepositoryFacts:
    source: str = ""
    source_type: str = ""
    repository_name: str = ""
    repository_kind: str = ""
    project_description: str = ""
    file_count: int = 0
    languages: list[str] = field(default_factory=list)
    technology_stack: dict[str, list[str]] = field(default_factory=dict)
    dependencies_by_scope: dict[str, list[Dependency]] = field(default_factory=dict)
    tests: TestAnalysis = field(default_factory=TestAnalysis)
    internal_apis: list[ApiEndpoint] = field(default_factory=list)
    external_calls: list[ExternalCall] = field(default_factory=list)
    artifacts: dict[str, list[str]] = field(default_factory=dict)
    important_files: list[str] = field(default_factory=list)
    repository_structure: dict[str, Any] = field(default_factory=dict)
    symbols: dict[str, Any] = field(default_factory=dict)
    architecture_facts: ArchitectureFacts = field(default_factory=ArchitectureFacts)
    readme_summary: str = ""

@dataclass
class SemanticResult:
    status: str = "Not run"
    repository_summary: str = ""
    what_repository_does: str = ""
    main_use_cases: list[dict[str, Any]] = field(default_factory=list)
    architecture_explanation: str = ""
    code_flow_explanation: list[str] = field(default_factory=list)
    # V8: detailed, user-friendly, repository-specific end-to-end code flow.
    overall_code_flow: list[dict[str, Any]] = field(default_factory=list)
    code_flow_status: str = "Not run"
    limitations: list[str] = field(default_factory=list)
