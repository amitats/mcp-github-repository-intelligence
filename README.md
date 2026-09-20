# MCP-Driven GitHub Repository Intelligence Automation

An MCP-driven repository analysis platform that converts a GitHub repository into structured technical intelligence and makes that intelligence available for natural-language exploration through an MCP-compatible AI client such as Claude Desktop.

The platform combines deterministic static repository analysis, selective local LLM processing, dependency/version enrichment, structured JSON/Markdown reporting, and MCP tools. Its main design principle is simple: **repository facts should come from repository evidence, not AI assumptions.**

---

## What This Project Does

The platform accepts a GitHub repository URL or local repository path and analyzes the codebase to build a technical view of the application.

It can analyze:

- Application purpose and repository structure
- Programming languages, frameworks and runtime technologies
- Important source files and components
- Application architecture and component relationships
- Application entry points
- Startup and initialization flow
- HTTP routes and handlers
- Service/use-case layers
- Repository and DAL/client layers
- Database operations
- External API and integration calls
- Dependencies and declared versions
- Current dependency/version information through MCP enrichment
- Tests, testing frameworks and available coverage evidence
- Swagger/OpenAPI definitions
- Docker and Docker Compose
- Kubernetes and Helm
- Terraform
- GitHub Actions and CI/CD configuration
- Main application use cases
- Runtime and graceful shutdown behavior
- Analysis limitations

For production runtime analysis, the analyzer attempts to resolve evidence-backed flows such as:

```text
HTTP Request
    -> Route
    -> Handler
    -> Validation / Input Parsing
    -> Service / Use Case
    -> Repository
    -> DAL / Client
    -> Database / External System
    -> Response
```

A transition is reported only when repository evidence supports it. Missing relationships are left unresolved instead of being invented.

---

## Why MCP Is Used

MCP acts as the integration layer between the repository-analysis engine, changing external technical information, and the conversational AI interface.

The repository analyzer provides relatively stable facts such as:

- code structure
- components
- architecture evidence
- APIs
- runtime flows
- dependencies
- tests
- infrastructure artifacts

MCP-based compatibility tooling is used for information that can change over time, such as:

- latest package versions
- runtime support information
- dependency update status
- upgrade information

An MCP-compatible client can then retrieve the generated repository intelligence without needing to understand the internal Python implementation or report format.

---

## High-Level Architecture

```text
GitHub Repository / Local Repository
                |
                v
        Repository Ingestion
                |
                v
        Repository Scanner
                |
                v
   Static Production Evidence Model
                |
        +-------+-------+
        |               |
        v               v
 Architecture /     Dependency &
 Runtime Analysis   Version Analysis
        |               |
        |          MCP Compatibility
        |            Enrichment
        +-------+-------+
                |
                v
      Structured Intelligence
         JSON + Markdown
                |
                v
            MCP Server
                |
                v
        MCP-Compatible Client
        e.g. Claude Desktop
                |
                v
 Natural-Language Repository Exploration
```

---

## Analysis Approach

### 1. Repository Ingestion

The workflow accepts either a GitHub repository URL or a local repository path.

For GitHub repositories, the project is retrieved and passed into the repository-analysis pipeline.

Private GitHub repositories can be accessed by supplying a GitHub token through the local `.env` configuration.

---

### 2. Repository Scanning

The scanner walks the repository and classifies technical artifacts such as:

- application source
- dependency manifests
- lock files
- configuration
- tests
- coverage artifacts
- Dockerfiles
- Docker Compose
- Kubernetes manifests
- Helm charts
- Terraform
- GitHub Actions
- Swagger/OpenAPI
- technical documentation

Tests, mocks, fixtures and examples are filtered from production runtime relationships where appropriate.

---

### 3. Technology Discovery

The analyzer uses repository evidence such as source files, imports, dependency definitions and configuration to identify technologies.

It attempts to determine:

- languages
- frameworks
- runtimes
- databases
- important libraries
- container technologies
- infrastructure technologies
- CI/CD
- testing tools
- monitoring/observability technologies

Technology information is reported only when supporting evidence is available.

---

### 4. Static Architecture Analysis

The analyzer builds a compact production runtime evidence model before semantic explanation.

It examines source structure and relationships to identify:

- packages
- modules
- classes
- functions/methods where supported
- imports
- routes
- handlers
- services/use cases
- repositories
- DAL/client components
- database operations
- external integrations
- startup/runtime components

Production relationships are kept separate from test and mock relationships.

---

### 5. Detailed Runtime Code Flow

The analyzer attempts to reconstruct actual application execution paths from repository evidence.

Important flows are separated rather than being collapsed into one generic request flow. Depending on the repository, these may include:

- create operations
- read operations
- update operations
- delete/archive operations
- configuration flows
- health flows
- metrics flows
- API request flows
- startup flows
- graceful shutdown flows

Request validation, business validation and important helper calls can also be included when detected.

If a complete transition cannot be established from source evidence, the analyzer reports the limitation rather than assuming a conventional architecture.

---

### 6. API and Integration Analysis

Swagger/OpenAPI is used as API documentation evidence, while source code remains the runtime implementation evidence.

The analyzer can identify:

- HTTP method
- endpoint/path
- owning handler/controller
- relevant source file
- downstream service/use-case flow where proven
- external API/client calls where proven

This helps distinguish documented API contracts from the code that actually implements runtime behavior.

---

### 7. Dependency and Compatibility Intelligence

Dependency manifests and supported package definitions are analyzed to extract package names and declared versions.

For detected dependencies, MCP-based compatibility enrichment can retrieve changing external information such as:

```text
Detected Dependency + Version
            |
            v
       MCP Lookup
            |
            v
     External Source
            |
            v
 Latest / Support Information
            |
            v
    Normalized Comparison
```

The implementation supports ecosystem-specific version lookup logic and normalized version comparison.

Compatibility states can include:

- `CURRENT`
- `UPDATE_AVAILABLE`
- `AHEAD_OF_LATEST`
- `UNKNOWN`

If a package or version cannot be reliably resolved, it remains unknown rather than being guessed.

---

## Selective Local LLM Usage

The project can use a local LLM through Ollama for semantic explanation.

The LLM is not intended to replace deterministic repository analysis.

Instead, a compact structured evidence model is passed to the model for tasks such as:

- repository summary
- use-case explanation
- detailed production runtime-flow explanation

The detailed-flow pass receives statically extracted runtime evidence rather than a large raw-source dump.

Console execution shows:

```text
[LLM 1/2] Repository summary/use cases
[LLM 2/2] Detailed production runtime flow
```

A deterministic fallback remains available if the semantic LLM stage fails.

---

## Repository Intelligence Output

The analyzer produces two main output files:

```text
analysis-output/
├── repository_analysis.json
└── repository_analysis.md
```

### `repository_analysis.json`

Machine-readable repository intelligence used by MCP tools and automation.

### `repository_analysis.md`

Human-readable technical analysis for engineers.

The generated intelligence can contain sections covering repository summary, technology stack, artifacts, components, architecture, runtime flow, dependencies, tests, APIs, integrations, use cases and analysis limitations.

---

## Repository-Aware MCP Integration

Repository analysis can be stored and retrieved independently so that multiple repositories can be analyzed without mixing their results.

The MCP layer exposes repository-intelligence functionality to the AI client.

Typical capabilities include:

```text
analyze_repository
list_analyzed_repositories
get_repository_analysis_status
get_repository_analysis
get_complete_repository_intelligence
get_code_architecture
get_detailed_code_flow
get_components_and_relationships
get_internal_apis
get_external_integrations
get_tests_and_coverage
get_main_use_cases
get_dependencies_and_compatibility
search_repository_analysis
```

Compatibility-related capabilities can include:

```text
get_latest_package_version
get_runtime_support
search_upgrade_information
```

This allows the AI client to request only the repository information required for a particular question.

---

## Claude Desktop Integration

Claude Desktop can be configured as the conversational interface for the repository-intelligence MCP server.

The interaction becomes:

```text
User
 |
 | GitHub repository URL + technical question
 v
Claude Desktop
 |
 v
MCP Repository Intelligence Server
 |
 +--> Analyze repository if required
 |
 +--> Retrieve stored repository intelligence
 |
 +--> Retrieve compatibility information where required
 |
 v
Claude Desktop
 |
 v
Natural-Language Technical Answer
```

This avoids building a separate chatbot frontend while still providing conversational access to the analysis.

---

## Example Questions

After the repository has been analyzed, an MCP-compatible client can request information such as:

```text
What does this application do?

Explain the complete technology stack.

Show the application architecture.

Explain the startup flow.

Show the end-to-end code flow.

Which APIs does this application expose?

Show the handler to service to repository flow.

Which databases does the application use?

Which external systems does it call?

What dependencies and versions are being used?

Are newer dependency versions available?

What tests exist in this repository?

What Docker, Kubernetes, Helm or Terraform configuration exists?

Explain the CI/CD implementation.

What are the main application use cases?

What could not be reliably determined from the repository?
```

---

## Requirements

- Python 3.10+
- Git
- Ollama for local semantic/code-flow explanation
- An MCP-compatible client for conversational exploration

---

## Setup

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

---

## Environment Configuration

Example `.env`:

```text
GITHUB_TOKEN=
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5-coder:7b
LLM_API_KEY=
MCP_SEARCH_URL=
MCP_SEARCH_TOKEN=
MAX_FILE_SIZE=700000
MAX_LLM_FILES=16
MAX_LLM_CHARS_PER_FILE=2800
MAX_LLM_TOTAL_CHARS=36000
LLM_MAX_TOKENS=2200
FLOW_LLM_MAX_TOKENS=5200
LLM_NUM_CTX=24576
REQUEST_TIMEOUT=240
```

Do not commit a real `.env` file containing credentials to Git.

For private repositories, configure `GITHUB_TOKEN` locally and pass the normal HTTPS GitHub repository URL to the analyzer.

---

## Run Against a GitHub Repository

```bash
python main.py \
  --source "https://github.com/<organization>/<repository>.git" \
  --output "./analysis-output" \
  --skip-compatibility
```

When evaluating the natural-language detailed code-flow explanation, do not use `--skip-llm`.

---

## Run Against a Local Repository

```bash
python main.py \
  --source "/path/to/local/repository" \
  --output "./analysis-output" \
  --skip-compatibility
```

---

## Expected Runtime Flow Output

For an HTTP service with sufficient source evidence, the generated Markdown report can describe flows in this form:

```text
HTTP method/path
    -> Handler
    -> Validation / Input Parsing
    -> Use Case / Service
    -> Repository
    -> DAL / Client
    -> Database / External Operation
    -> Result / Response
```

The analyzer must not invent missing transitions.

If repository evidence cannot resolve part of the chain, the report should identify that limitation.

---

## Key Design Principles

### Evidence First

Source code and repository artifacts are the primary source of truth.

### No Invented Architecture

Missing relationships, functions, APIs or code-flow transitions are not filled with assumed framework conventions.

### Deterministic Analysis Before AI

Static repository intelligence is built before the LLM is asked to explain it.

### Separate Static and Changing Information

Repository facts come from repository analysis. Changing package/version/support information is retrieved separately through MCP-compatible external lookup logic.

### Production-Focused Analysis

Tests, mocks, fixtures and examples are prevented from incorrectly defining the production architecture wherever the analyzer can distinguish them.

### Transparent Limitations

When the analyzer cannot reliably determine something, the generated report explicitly states that limitation.

---

## End-to-End Workflow

```text
GitHub Repository URL
        |
        v
Repository Ingestion
        |
        v
File Scanning & Classification
        |
        v
Technology Discovery
        |
        v
Production Runtime Evidence Extraction
        |
        +-------------------------+
        |                         |
        v                         v
Architecture Analysis      Dependency Analysis
        |                         |
        v                         v
Detailed Code Flow        MCP Compatibility Lookup
        |                         |
        +------------+------------+
                     |
                     v
          Repository Intelligence
             JSON + Markdown
                     |
                     v
                MCP Server
                     |
                     v
              Claude Desktop
                     |
                     v
       Natural-Language Exploration
```

---

## Project Outcome

The completed platform turns a GitHub repository or local codebase into structured, queryable technical intelligence.

It combines deterministic repository analysis with selective local LLM explanation and MCP-based enrichment so engineers can move from:

```text
GitHub Repository
```

to:

```text
Architecture
+ Code Flow
+ APIs
+ Integrations
+ Dependencies
+ Compatibility
+ Tests
+ Infrastructure
+ CI/CD
+ Use Cases
+ Analysis Limitations
```

and then explore that information conversationally through an MCP-compatible AI client.

The goal is not to ask an AI model to guess how a codebase works. The goal is to **extract technical evidence first, structure it, enrich changing information through controlled MCP tools, and then use AI to make that evidence easier to explore and understand.**
