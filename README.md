# Repository Intelligence Analyzer 

- Builds a compact **production runtime evidence model** before calling the local LLM.
- Resolves HTTP route -> handler -> use case/service -> repository -> DAL/client -> database operations where source proves that chain.
- Extracts request/business validation conditions and important helper calls.
- Separates Create/Read/Update/Delete/archive/config/health/metrics/etc. flows instead of collapsing everything into a generic request flow.
- Extracts startup, server/router/middleware lifecycle and graceful shutdown evidence.
- Filters tests, mocks, fixtures and examples from production architecture relationships and runtime flow.
- Uses Swagger/OpenAPI as endpoint documentation evidence while keeping source code as runtime implementation evidence.
- Reconciles framework/database/test detection (for example Gin, MongoDB and Testify when present in dependency/source evidence).
- Uses a compact structured LLM context instead of feeding up to 45 large source-file digests. The detailed-flow pass runs once; deterministic detailed runtime fallback is available if the LLM fails.
- Keeps exactly two output files: `repository_analysis.json` and `repository_analysis.md`.

## Requirements

- Python 3.10+
- Git
- Ollama for local semantic/code-flow explanation

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell activation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

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

For a private GitHub repository, put the token only in `.env` as `GITHUB_TOKEN`. Use the normal HTTPS repository URL on the command line.

## Test against GitHub

```bash
python main.py \
  --source "https://github.com/NBCUDTC/midnight-metalist-service-src.git" \
  --output "./analysis-output" \
  --skip-compatibility
```

Do **not** add `--skip-llm` when evaluating the detailed natural-language code-flow explanation.

## Test against a local repository

```bash
python main.py \
  --source "/path/to/local/repository" \
  --output "./analysis-output" \
  --skip-compatibility
```

## Expected output

```text
analysis-output/
├── repository_analysis.json
└── repository_analysis.md
```

Check `## 6. Overall Code Flow` in the Markdown report. For an HTTP service with enough source evidence, the analyzer should explain application startup and then separate important endpoint flows using the proven production chain, for example:

```text
HTTP method/path
  -> Handler
  -> validation/input parsing
  -> Use case / service
  -> Repository
  -> DAL/client
  -> database/external operation
  -> result/response
```

The analyzer must not invent missing transitions. If source evidence cannot resolve part of a flow, the report should say that rather than assume a conventional architecture.

## Faster LLM behavior

At step `[6/8]` the console now shows two sub-steps:

```text
[LLM 1/2] Repository summary/use cases
[LLM 2/2] Detailed production runtime flow
```

The second pass receives compact statically extracted runtime evidence instead of a large raw-source dump. `FLOW_LLM_MAX_TOKENS` controls the maximum detailed-flow response size and `LLM_NUM_CTX` controls the Ollama context window.
