# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

[![English](https://img.shields.io/badge/lang-en-blue.svg)](README.md) [![中文](https://img.shields.io/badge/lang-zh-blue.svg)](lang/README.zh.md) [![हिंदी](https://img.shields.io/badge/lang-hi-blue.svg)](lang/README.hi.md) [![Español](https://img.shields.io/badge/lang-es-blue.svg)](lang/README.es.md) [![Français](https://img.shields.io/badge/lang-fr-blue.svg)](lang/README.fr.md) [![العربية](https://img.shields.io/badge/lang-ar-blue.svg)](lang/README.ar.md) [![বাংলা](https://img.shields.io/badge/lang-bn-blue.svg)](lang/README.bn.md) [![Русский](https://img.shields.io/badge/lang-ru-blue.svg)](lang/README.ru.md) [![Português](https://img.shields.io/badge/lang-pt-blue.svg)](lang/README.pt.md) [![Bahasa Indonesia](https://img.shields.io/badge/lang-id-blue.svg)](lang/README.id.md)

![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A powerful web crawling tool that integrates with AI assistants via the MCP (Model Context Protocol). This project allows AI assistants to crawl websites, extract dynamic content, navigate through links, and save structured Markdown files directly.

## 📋 Features

- Native integration with AI assistants via MCP
- Return scraped Markdown content directly to the AI
- Extracts and surfaces internal/external links for AI navigation
- Website crawling with configurable depth and page limit
- Detailed crawl result statistics, including the list of skipped pages
- Live progress notifications during long crawls
- Saved results exposed as MCP resources (`crawl://results/...`)
- Error and not found page handling
- Secure by default: only public http(s) URLs, JavaScript disabled unless you opt in
- **Advanced Scraping Capabilities**:
  - **Magic Mode**: crawl4ai heuristics that simulate a real browser and help with some anti-bot protections (not a guaranteed bypass)
  - **Targeted Extraction**: Fetch only what you need using CSS selectors
  - **Custom JavaScript** (opt-in): Execute code before extraction (clicks, scrolls, form fills)
  - **Persistent Sessions**: One browser is shared across calls, so a `session_id` keeps cookies and state until it is closed (`close_session`) or stays idle too long
  - **SPA Support**: Wait for dynamic CSS selectors or set explicit pre-extraction delays

## 🚀 MCP Configuration

The simplest and recommended way to use this tool is via `uvx`. The `@latest` suffix makes `uvx` check PyPI at each start and run the newest published version (without it, `uvx` keeps reusing the version it cached the first time).

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed on your system.

### Setup for AI Assistants (e.g., Claude Desktop, Cline)

Add the following to your AI Assistant's MCP configuration file (e.g., `cline_mcp_settings.json` or `claude_desktop_config.json`):

> **Note**: Python 3.12 or 3.13 is required (crawl4ai does not support 3.14 yet). Specifying `--python 3.13` is recommended, especially on Windows, to avoid compilation issues with certain dependencies.

**From PyPI (recommended):**

```json
{
  "mcpServers": {
    "crawl": {
      "command": "uvx",
      "args": [
        "--python",
        "3.13",
        "crawl4ai-mcp-llm@latest"
      ],
      "disabled": false,
      "autoApprove": [],
      "timeout": 600
    }
  }
}
```

**From GitHub (latest unreleased):**

```json
{
  "mcpServers": {
    "crawl": {
      "command": "uvx",
      "args": [
        "--python",
        "3.13",
        "--from",
        "git+https://github.com/laurentvv/crawl4ai-mcp-llm",
        "crawl4ai-mcp-llm"
      ],
      "disabled": false,
      "autoApprove": [],
      "timeout": 600
    }
  }
}
```

**Claude Code:**

```bash
claude mcp add crawl -s user -- uvx --python 3.13 crawl4ai-mcp-llm@latest
```

### Important: Browser Installation

The crawler uses Playwright to handle dynamic content. Install Chromium once after setting up the tool:

```bash
# When running the server with uvx (recommended setup)
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium

# From a local clone
uv run playwright install chromium
```

## 🖥️ Usage

Once configured, you can use the crawler by asking your AI assistant to perform a crawl.

### Usage Examples with Claude/Cline

- **Single Page**: "Fetch https://docs.python.org/3/library/re.html (just that page) and summarize it."
- **Simple Crawl**: "Can you crawl the site example.com and give me a summary?"
- **Crawl with Options**: "Can you crawl https://example.com with a depth of 3 and include external links?"
- **Dynamic Content**: "Crawl this React app and wait for the `.main-content` selector to load."
- **Anti-bot Heuristics**: "Crawl example.com with magic mode enabled."
- **Targeted Extraction**: "Crawl the docs site but only extract content matching the `h1, p.lead` CSS selector."

## 🧰 Tools and Resources

| Tool | Purpose |
|------|---------|
| `crawl` | Crawl a site (following links up to `max_depth`/`max_pages`), save the result as Markdown and return a summary with the content |
| `crawl_page` | Fetch exactly one page and return its Markdown, without following links or writing any file (faster for "read this page" requests) |
| `close_session` | Close a browser session opened with `session_id` (idle sessions are also closed automatically after `CRAWL4AI_MCP_SESSION_TTL`) |

| Resource | Content |
|----------|---------|
| `crawl://results` | JSON list of saved results (URI, name, size, date, source URL), newest first |
| `crawl://results/{path}` | Full Markdown of a saved result, e.g. `crawl://results/crawl_example_com_20260101_120000_ab12cd.md` |

The `crawl` response includes the resource URI of its result: when the returned content is truncated, the assistant can read the complete file through that resource even if it has no access to the server's file system.

**Progress:** `crawl` sends an MCP progress notification after each page. Clients that reset their timeout on progress can use a shorter timeout; otherwise keep a generous one (e.g. 600 s).

## 🛠️ Available Parameters (`crawl` tool)

The `crawl` tool accepts the following parameters (`crawl_page` accepts `url`, `css_selector`, `wait_for_selector`, `magic`, `session_id`, `delay_before_return_html` and `max_content_chars`):

| Parameter | Type | Description | Default Value |
|-----------|------|-------------|---------------|
| `url` | string | http(s) URL to crawl (required). A bare domain such as `example.com` is treated as `https://example.com`. | - |
| `max_depth` | integer | Link depth to follow (0-5): `0` = start page only, `1` = the start page and its links, and so on | 2 |
| `max_pages` | integer | Maximum number of pages to crawl (1-500). `1` fetches exactly one page. | 50 |
| `include_external` | boolean | Also follow links to other domains | false |
| `wait_for_selector` | string | CSS selector to wait for before extracting content. Useful for single-page applications. | None |
| `return_content` | boolean | Return the extracted content directly in the MCP response | true |
| `max_content_chars` | integer | Maximum number of content characters returned in the response (1,000-500,000); the file always holds everything | 50000 |
| `output_file` | string | Markdown file name, always stored inside the results directory (`.md` is added if missing) | automatically generated |
| `overwrite` | boolean | Allow replacing an existing `output_file` | false |
| `magic` | boolean | Enable crawl4ai magic mode (anti-bot heuristics) | false |
| `css_selector` | string | Specific CSS selector to extract only targeted elements from the page | None |
| `js_code` | string | Custom JavaScript code to execute before extraction (requires `CRAWL4AI_MCP_ALLOW_JS=true`) | None |
| `session_id` | string | Reuse cookies and browser state across calls with the same id | None |
| `delay_before_return_html` | number | Delay in seconds (0-60) before extracting HTML (useful for heavy JS pages) | None |

## ⚙️ Configuration (environment variables)

Set these in the `env` section of your MCP configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `CRAWL4AI_RESULTS_DIR` | Directory where Markdown results are written | `~/.crawl4ai_mcp_llm/results` |
| `CRAWL4AI_MCP_ALLOW_JS` | Allow `js_code` and JavaScript wait conditions (`js:...`) | `false` |
| `CRAWL4AI_MCP_ALLOW_PRIVATE_NETWORKS` | Allow crawling `localhost` and private/link-local addresses | `false` |
| `CRAWL4AI_MCP_CRAWL_TIMEOUT` | Maximum duration of one crawl, in seconds (pages crawled so far are kept) | `300` |
| `CRAWL4AI_MCP_MAX_CONCURRENT_CRAWLS` | Maximum number of crawls running at the same time | `2` |
| `CRAWL4AI_MCP_SESSION_TTL` | Seconds after which an unused browser session (`session_id`) is closed | `1800` |
| `CRAWL4AI_MCP_VERBOSE` | Enable crawl4ai's detailed progress logs (on stderr) | `false` |
| `CRAWL4AI_MCP_LOG_LEVEL` | Server log level (`DEBUG`, `INFO`, `WARNING`, ...) | `INFO` |

## 🔒 Security

The AI assistant decides which URLs are crawled, and crawled pages may contain prompt-injection attempts. The server therefore:

- only accepts `http`/`https` URLs (no `file://`, `raw:`, `data:` ...), and rejects hosts resolving to loopback, private or link-local addresses unless `CRAWL4AI_MCP_ALLOW_PRIVATE_NETWORKS=true`;
- runs no custom JavaScript (including `js:` wait conditions) unless `CRAWL4AI_MCP_ALLOW_JS=true`;
- writes files only inside the results directory and never overwrites them without `overwrite=true`;
- wraps returned page content in `<untrusted-web-content>` tags so the assistant treats it as data.

Redirects and links discovered during a deep crawl are filtered on their URL only (no DNS lookup): keep private-network access disabled when the server can reach sensitive internal services.

## 👨‍💻 Development

If you want to modify the crawler or run it locally:

1. Clone this repository:
```bash
git clone https://github.com/laurentvv/crawl4ai-mcp-llm
cd crawl4ai-mcp-llm
```

2. Install dependencies using `uv`:
```bash
uv sync
```

3. Test the MCP server locally using the official MCP Inspector:
```bash
npx -y @modelcontextprotocol/inspector uv run crawl4ai-mcp-llm
```

4. Run the checks (unit tests never hit the network):
```bash
uv run pytest --cov                # unit tests + coverage report (80% minimum)
uv run pytest -m integration       # real crawls, needs network and Chromium
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

5. Run the MCP server directly (for standard usage):
```bash
uv run crawl4ai-mcp-llm
```

Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## 🤝 Contribution

Contributions are welcome! Feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

[![Glama MCP](https://glama.ai/mcp/servers/@laurentvv/crawl4ai-mcp-llm/badge)](https://glama.ai/mcp/servers/@laurentvv/crawl4ai-mcp-llm)
