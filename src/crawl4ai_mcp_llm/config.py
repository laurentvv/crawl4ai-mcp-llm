"""Centralised runtime settings, read from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

RESULTS_DIR_ENV = "CRAWL4AI_RESULTS_DIR"
ALLOW_JS_ENV = "CRAWL4AI_MCP_ALLOW_JS"
ALLOW_PRIVATE_NETWORKS_ENV = "CRAWL4AI_MCP_ALLOW_PRIVATE_NETWORKS"
CRAWL_TIMEOUT_ENV = "CRAWL4AI_MCP_CRAWL_TIMEOUT"
MAX_CONCURRENT_CRAWLS_ENV = "CRAWL4AI_MCP_MAX_CONCURRENT_CRAWLS"
VERBOSE_ENV = "CRAWL4AI_MCP_VERBOSE"
LOG_LEVEL_ENV = "CRAWL4AI_MCP_LOG_LEVEL"
SESSION_TTL_ENV = "CRAWL4AI_MCP_SESSION_TTL"

DEFAULT_RESULTS_DIR = "~/.crawl4ai_mcp_llm/results"
DEFAULT_CRAWL_TIMEOUT = 300.0
DEFAULT_MAX_CONCURRENT_CRAWLS = 2
DEFAULT_SESSION_TTL = 1800.0


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_number[T: (int, float)](name: str, default: T, cast: type[T]) -> T:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = cast(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class Settings:
    results_dir: Path
    allow_js: bool
    allow_private_networks: bool
    crawl_timeout: float
    max_concurrent_crawls: int
    verbose: bool
    log_level: str
    session_ttl: float


def get_settings() -> Settings:
    """Build the settings from the current environment.

    Cheap enough to call per request, which keeps the server reactive to
    environment changes (and lets tests override variables with monkeypatch).
    """
    results_dir = os.getenv(RESULTS_DIR_ENV) or DEFAULT_RESULTS_DIR
    return Settings(
        results_dir=Path(results_dir).expanduser().resolve(),
        allow_js=_env_bool(ALLOW_JS_ENV),
        allow_private_networks=_env_bool(ALLOW_PRIVATE_NETWORKS_ENV),
        crawl_timeout=_env_number(CRAWL_TIMEOUT_ENV, DEFAULT_CRAWL_TIMEOUT, float),
        max_concurrent_crawls=_env_number(MAX_CONCURRENT_CRAWLS_ENV, DEFAULT_MAX_CONCURRENT_CRAWLS, int),
        verbose=_env_bool(VERBOSE_ENV),
        log_level=(os.getenv(LOG_LEVEL_ENV) or "INFO").upper(),
        session_ttl=_env_number(SESSION_TTL_ENV, DEFAULT_SESSION_TTL, float),
    )
