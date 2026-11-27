# Crawl4AI MCP Plugin for Antigravity

This directory packages [`crawl4ai-mcp-llm`](https://github.com/laurentvv/crawl4ai-mcp-llm) as an Antigravity plugin with interactive MCP Apps:

- **Inline Crawl Card** (`crawl`, `crawl_page`): displays crawl status, page/error counters, rendered or raw Markdown preview, filterable links, skipped pages, and quick actions (copy, attach to next message, open saved `.md` file in the side panel).
- **Crawl4AI Explorer** (`open_crawl_explorer`, `aux_pane` + `global` entrypoints): browse and search saved Markdown results (by filename/URL or full text), inspect individual crawled pages, run new single-page or deep crawls with URL include/exclude patterns, and close active browser sessions.
- **Crawl4AI File Viewer** (`view_crawl_file`, `file` entrypoint for `.crawlmd` / `.crawl.md`): opens exported crawl files with a per-page table of contents, metadata, and one-click re-crawl.

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="Crawl4AI MCP Apps in Antigravity: Inline Crawl Card and Crawl4AI Explorer side panel" width="900"/>
</div>

## Prerequisites

- [`uv`](https://github.com/astral-sh/uv) installed on your system
- Chromium installed once for Playwright:

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## Validate and install

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

For local development from a git checkout, point the installed plugin's `mcp_config.json` to `uv --directory <repo-path> run crawl4ai-mcp-llm` and optionally set `CRAWL4AI_MCP_UI_DIR` to iterate on compiled HTML files without rebuilding the package.
