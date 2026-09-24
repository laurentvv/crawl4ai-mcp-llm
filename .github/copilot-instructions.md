# Contributing guidelines for AI assistants

This repository is an MCP (Model Context Protocol) server that exposes Crawl4AI
web crawling over stdio. Keep changes small and idiomatic.

## Layout
- `src/crawl4ai_mcp_llm/server.py` — MCP tool definition (`crawl`), response formatting, shared-browser lifespan.
- `src/crawl4ai_mcp_llm/crawler.py` — crawl orchestration (crawl4ai config, streaming, timeouts, stats).
- `src/crawl4ai_mcp_llm/security.py` — URL / output path / wait condition validation.
- `src/crawl4ai_mcp_llm/markdown.py` — Markdown cleaning and page formatting.
- `src/crawl4ai_mcp_llm/config.py` — settings read from `CRAWL4AI_*` environment variables.

## Rules
- Never write to stdout: it carries the MCP protocol. Use `logging` (configured on stderr).
- Every new crawl option exposed to the LLM goes through validation in `security.py`
  and keeps JavaScript execution behind `CRAWL4AI_MCP_ALLOW_JS`.
- The tool docstring is sent to the LLM as the tool description: keep it a plain
  string literal (not an f-string) and up to date.
- Tests must not hit the network: use the `fake_crawler` fixture from `tests/conftest.py`.

## Commands
- `uv sync` — install
- `uv run pytest` — unit tests (`uv run pytest -m integration` for real crawls)
- `uv run ruff check . && uv run ruff format --check . && uv run mypy` — lint and types
