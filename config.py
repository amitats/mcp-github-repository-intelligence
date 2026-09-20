import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://localhost:11434").rstrip("/")
    llm_model: str = os.getenv("LLM_MODEL", "qwen2.5-coder:7b")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    mcp_search_url: str = os.getenv("MCP_SEARCH_URL", "")
    mcp_search_token: str = os.getenv("MCP_SEARCH_TOKEN", "")
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "700000"))
    max_llm_files: int = int(os.getenv("MAX_LLM_FILES", "16"))
    max_llm_chars_per_file: int = int(os.getenv("MAX_LLM_CHARS_PER_FILE", "2800"))
    max_llm_total_chars: int = int(os.getenv("MAX_LLM_TOTAL_CHARS", "36000"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2200"))
    flow_llm_max_tokens: int = int(os.getenv("FLOW_LLM_MAX_TOKENS", "5200"))
    llm_num_ctx: int = int(os.getenv("LLM_NUM_CTX", "24576"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "240"))

settings = Settings()
