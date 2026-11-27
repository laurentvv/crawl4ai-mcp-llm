# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-11-27

### Added
- Interactive **MCP Apps** support (`io.modelcontextprotocol/ui` + Antigravity `com.google.antigravity/ui`):
  - Inline crawl card UI (`ui://crawl4ai/crawl-card.html`) attached to `crawl` and `crawl_page` with `structuredContent` alongside existing plain-text responses.
  - Side-panel (`aux_pane`) and full-page (`global`) **Crawl4AI Explorer** (`open_crawl_explorer`, `ui://crawl4ai/explorer.html`) to browse saved Markdown results (paginated at 200 items with server-side filename/URL and full-text search), navigate multi-page crawls per page (with per-page copy/attach/re-crawl), run new crawls, and manage browser sessions.
  - Custom Antigravity file viewer (`view_crawl_file`, `ui://crawl4ai/file-viewer.html`, `entrypoint: file` for `.crawlmd` / `.crawl.md`) with page TOC, metadata, and one-click live re-crawl.
  - Read-only app helpers (`app_list_results` with `query`/`offset`/`limit`, `app_search_results` for full-text search, `app_read_result`, `visibility: ["app"]`).
  - Glob URL filtering on `crawl` via `include_patterns` and `exclude_patterns` (`PatternURLFilter`).
  - Frontend Vitest unit test suite (`ui/src/shared.test.ts`) verifying Markdown XSS protection and multi-page crawl parsing.
  - `CRAWL4AI_MCP_UI_DIR` environment variable to override packaged HTML bundles during local UI iteration.
  - Antigravity plugin packaging under `plugin/` (`plugin.json`, `mcp_config.json`, `assets/logo.svg`).

### Changed
- Upgraded locked Python dependencies to latest compatible releases (`crawl4ai` 0.9.6, `mcp` 2.3.0, `playwright` 1.65.2, `pydantic` 2.14.4, `anyio` 4.16.0, `ruff` 0.17.6, `mypy` 2.4.1, `pytest` 9.2.0; `pip-audit` clean) and raised `mcp` floor to `>=2.2.0,<3`.
- Sped up `list_results()` on large result folders by running the scan in a single worker thread and caching `source_url` headers by `(path, mtime_ns, size)`.
- Markdown page timestamps now use explicit UTC ISO-8601 (`datetime.now(UTC)`).

### Fixed
- `sanitize_for_display()` now actually applies its ASCII/Unicode translation table instead of catching an unreachable UTF-8 `UnicodeEncodeError`.
- Bare domains passed to `crawl` / `crawl_page` (e.g. `example.com`) now surface as normalized `https://` URLs in both the text summary and inline card.
- Guarded `CrawlerManager.close()` with the startup lock and `Explorer` document loads with a sequence guard against out-of-order responses.
- Protected inline code spans and added ordered-list / empty-bullet handling in the MCP App safe Markdown renderer.

## [0.2.2] - 2026-09-24

### Documentation
- The recommended `uvx` setup now uses `crawl4ai-mcp-llm@latest`: without it, `uvx` keeps running the version it cached first. Added the Claude Code setup command.

## [0.2.1] - 2026-09-24

### Fixed
- `crawl_page` returned no content, and `crawl` returned one page fewer than `max_pages`: crawl4ai's streaming BFS stops before yielding the page that reaches its `max_pages` limit. The server now asks crawl4ai for one extra page and stops at exactly `max_pages` itself.

## [0.2.0] - 2026-09-24

### Security
- Only `http`/`https` start URLs are accepted: `file://`, `raw:`, `data:` and other schemes are rejected.
- Hosts resolving to loopback, private or link-local addresses are rejected unless `CRAWL4AI_MCP_ALLOW_PRIVATE_NETWORKS=true`; links discovered during deep crawls are filtered the same way (by URL, without DNS lookup).
- JavaScript wait conditions (`js:...`, function-like strings) now require `CRAWL4AI_MCP_ALLOW_JS=true`, like `js_code`; other values are pinned to `css:` selectors.
- `output_file` is sanitised, always gets a `.md` extension and no longer overwrites existing files unless `overwrite=true`.
- Returned page content is wrapped in `<untrusted-web-content>` tags.
- Locked dependencies upgraded to fix known vulnerabilities (aiohttp, cryptography, h2, httpx2, nltk, soupsieve).

### Fixed
- The `crawl` tool description was empty (its docstring was an f-string): MCP clients now receive the full usage and performance guidance.
- `max_depth=0` is accepted and fetches only the start page; the documentation now matches crawl4ai's depth semantics.
- Legitimate pages whose title merely mentions an error (e.g. "Forbidden Planet") are no longer skipped as 403/404 pages.
- Crash when a crawl result had `metadata=None`.
- Result file names are valid on Windows (no `:`), handle bare domains and are unique within the same second.
- The response no longer reports "completed successfully" when no page could be extracted, and no longer points to a non-existent `crawl_results` folder.

### Changed
- One browser is shared across tool calls (started lazily, closed on shutdown), so `session_id` now persists between calls and later crawls start faster.
- Pages are streamed and written as they are crawled; a crawl stops after `CRAWL4AI_MCP_CRAWL_TIMEOUT` seconds (default 300) and keeps the pages already written.
- At most `CRAWL4AI_MCP_MAX_CONCURRENT_CRAWLS` crawls (default 2) run at the same time.
- Tool errors are reported as MCP errors (`isError: true`) instead of plain "Error: ..." text.
- Tool parameters are validated (`max_depth` 0-5, `max_pages` 1-500, `delay_before_return_html` 0-60); `max_pages` defaults to 50.
- New tool parameters: `max_content_chars` and `overwrite`. The `verbose` parameter was removed from the tool (use `CRAWL4AI_MCP_VERBOSE`).
- The response lists skipped pages with the reason.
- Logging uses the standard `logging` module on stderr (`CRAWL4AI_MCP_LOG_LEVEL`); importing the package no longer replaces `sys.stdout`/`sys.stderr`.
- Supported Python versions: 3.12 and 3.13. Unused direct dependencies (`chardet`, `httpx`, `lxml`, `urllib3`) were removed and `crawl4ai>=0.9.2` is required.

### Added
- `crawl_page` tool: fetch a single page and return its Markdown without writing a file.
- `close_session` tool, and automatic closing of browser sessions idle for more than `CRAWL4AI_MCP_SESSION_TTL` seconds (default 1800).
- MCP progress notifications after each crawled page.
- Saved results are exposed as MCP resources: `crawl://results` (listing) and `crawl://results/{path}` (content); the `crawl` response links its result.
- When the client cancels a crawl, the partial result file is flushed and marked as cancelled.
- CI (lint, type check, tests on Linux and Windows, dependency audit), release workflow with PyPI Trusted Publishing, Dependabot.

## [0.1.6]

- Last release before this changelog was introduced.
