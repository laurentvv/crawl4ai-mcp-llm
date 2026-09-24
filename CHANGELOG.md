# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
