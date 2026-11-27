# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.svg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ [英文 README](../README.md) 为参考版本（环境变量、安全、开发）。

一款强大的网页抓取工具，通过 MCP（Model Context Protocol，模型上下文协议）与 AI 助手集成。本项目使 AI 助手能够抓取网站、提取动态内容、遍历链接，并直接保存结构化的 Markdown 文件。

## 📋 功能特性

- 通过 MCP 与 AI 助手原生集成（`crawl`、`crawl_page`、`close_session`、`open_crawl_explorer`、`view_crawl_file`）
- 将抓取到的 Markdown 内容直接返回给 AI，并将保存的结果作为 MCP 资源暴露（`crawl://results/...`）
- 提取并展示内部/外部链接，便于 AI 导航
- 支持可配置深度和页面上限的网站抓取、实时进度通知与详细统计
- **交互式 MCP Apps（Antigravity / SEP-1865）** — 已预打包在 wheel 中（无需 Node.js）：
  - `crawl` 与 `crawl_page` 的 **内联结果卡片**（状态、指标、Markdown 渲染/源码预览、可筛选链接、跳过页面）
  - **Crawl4AI Explorer**（`open_crawl_explorer`，侧边栏与全屏视图）：分页浏览已保存结果、按文件名/URL 及 **全文搜索**、**分页目录（TOC）**（单页复制/附加到对话）、交互式抓取表单与会话管理
  - **自定义文件查看器**（`view_crawl_file`，支持 `.crawlmd` / `.crawl.md`）：分页目录、元数据与一键重新抓取
  - 对非 UI 的 MCP 客户端保持 100% 纯文本向后兼容

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/mcp-apps-preview.png" alt="Antigravity 中的 Crawl4AI MCP Apps：内联卡片与 Crawl4AI Explorer 侧边栏" width="900"/>
</div>

- 错误和 404 页面的处理
- **高级抓取能力**：
  - **URL Glob 过滤**：通过 `include_patterns` 和 `exclude_patterns` 精确包含或排除路径
  - **Magic 模式**：crawl4ai 启发式策略，模拟真实浏览器行为以协助应对部分反爬保护
  - **定向提取**：通过 CSS 选择器仅获取所需内容
  - **自定义 JavaScript**（可选开启）：在提取前执行代码（需 `CRAWL4AI_MCP_ALLOW_JS=true`）
  - **持久会话**：共享浏览器跨调用保留 cookies 和状态（`session_id`）
  - **SPA 支持**：等待动态 CSS 选择器加载，或设置明确的提取前延迟

## 🚀 MCP 配置

最简单且推荐的使用方式是通过 `uvx`。使用 `@latest` 后缀可确保每次启动时运行 PyPI 上的最新版本。

### 前置条件

- 系统中已安装 [uv](https://github.com/astral-sh/uv)。

### AI 助手配置（Claude Desktop、Cline、Antigravity）

将以下内容添加到你 AI 助手的 MCP 配置文件中（`cline_mcp_settings.json`、`claude_desktop_config.json` 或 `mcp_config.json`）：

> **注意**：需要 Python 3.12 或 3.13。强烈建议指定 `--python 3.13`（尤其是在 Windows 上）。

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

**Claude Code：**

```bash
claude mcp add crawl -s user -- uvx --python 3.13 crawl4ai-mcp-llm@latest
```

**Google Antigravity（含 MCP Apps 插件）：**

```bash
agy plugin validate ./plugin --strict
agy plugin install ./plugin
```

### 重要提示：浏览器安装

抓取工具使用 Playwright 来处理动态内容。在配置完成后安装一次 Chromium：

```bash
uvx --python 3.13 --from crawl4ai-mcp-llm@latest playwright install chromium
```

## 🖥️ 使用方法

配置完成后，你可以通过让 AI 助手执行抓取来使用该工具。

### 使用示例

- **单页读取**："读取 https://docs.python.org/3/library/re.html（仅该页）并做个摘要。"
- **简单抓取**："你能抓取 example.com 网站并给我一个摘要吗？"
- **带选项抓取**："你能以深度 3 抓取 https://example.com 并包含外部链接吗？"
- **URL 过滤**："抓取 https://example.com，设置 `include_patterns=['/docs/*']` 且 `exclude_patterns=['/docs/legacy/*', '*.pdf']`。"
- **动态内容**："抓取这个 React 应用，并等待 `.main-content` 选择器加载完成。"
- **定向提取**："抓取文档网站，但仅提取匹配 `h1, p.lead` CSS 选择器的内容。"
- **交互式浏览器（Antigravity）**："打开 Crawl4AI Explorer 搜索我保存的抓取结果。"

## 🛠️ 可用参数（`crawl` 工具）

`crawl` 工具接受以下参数：

| 参数 | 类型 | 说明 | 默认值 |
|-----------|------|-------------|---------------|
| `url` | string | 要抓取的 http(s) URL（必填） | - |
| `max_depth` | integer | 要跟随的链接深度（0-5）：0 = 仅起始页面，1 = 其链接，依此类推 | 2 |
| `max_pages` | integer | 要爬取的最大页面数（1-500） | 50 |
| `include_external` | boolean | 包含外部链接 | false |
| `wait_for_selector` | string | 在提取内容前等待的 CSS 选择器。适用于单页应用。 | None |
| `return_content` | boolean | 是否直接在 MCP 响应中返回提取的内容 | true |
| `max_content_chars` | integer | 响应中返回内容的最大字符数（1,000-500,000） | 50000 |
| `output_file` | string | Markdown 文件名，始终保存在结果目录中 | 自动生成 |
| `overwrite` | boolean | 允许覆盖已存在的 `output_file` | false |
| `magic` | boolean | 启用 crawl4ai magic 模式（反爬启发式） | false |
| `css_selector` | string | 指定 CSS 选择器，仅从页面中提取目标元素 | None |
| `js_code` | string | 在提取前执行的自定义 JavaScript 代码（需 `CRAWL4AI_MCP_ALLOW_JS=true`） | None |
| `session_id` | string | 持久会话标识符，用于在请求之间保持 cookies 和浏览器状态 | None |
| `delay_before_return_html` | number | 提取 HTML 前等待的延迟秒数（0-60，适用于 JS 较多的页面） | None |
| `include_patterns` | array of strings | 仅跟随匹配至少一个 glob 模式的 URL（如 `["/docs/*", "*/api/*"]`） | None |
| `exclude_patterns` | array of strings | 跳过匹配任意 glob 模式的 URL（如 `["/blog/*", "*.pdf"]`），优先于 `include_patterns` | None |

## 📄 许可证

本项目基于 MIT 许可证授权。

---

> 🏠 **源代码与文档**：[github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
