# Web Crawler MCP

<div align="center">
  <img src="https://raw.githubusercontent.com/laurentvv/crawl4ai-mcp-llm/main/assets/banner.jpg" alt="Crawl4AI MCP Banner" width="800"/>
</div>

> ℹ️ [英文 README](../README.md) 为参考版本（环境变量、安全、开发）。

一款强大的网页抓取工具，通过 MCP（Model Context Protocol，模型上下文协议）与 AI 助手集成。本项目使 AI 助手能够抓取网站、提取动态内容、遍历链接，并直接保存结构化的 Markdown 文件。

## 📋 功能特性

- 通过 MCP 与 AI 助手原生集成
- 将抓取到的 Markdown 内容直接返回给 AI
- 提取并展示内部/外部链接，便于 AI 导航
- 支持可配置深度的网站抓取
- 详细的抓取结果统计
- 错误和 404 页面的处理
- **高级抓取能力**：
  - **Magic 模式**：绕过反爬虫机制（如 Cloudflare），模拟真实浏览器行为
  - **定向提取**：通过 CSS 选择器仅获取所需内容
  - **自定义 JavaScript**：在提取前执行代码（点击、滚动、填写表单）
  - **持久会话**：跨请求保持 cookies 和状态，适用于需要登录的网站
  - **SPA 支持**：等待动态 CSS 选择器加载，或设置明确的提取前延迟

## 🚀 MCP 配置

最简单且推荐的使用方式是通过 `uvx`，它会自动获取并运行 PyPI 上发布的最新版本。

### 前置条件

- 系统中已安装 [uv](https://github.com/astral-sh/uv)。

### AI 助手配置（例如 Claude Desktop、Cline）

将以下内容添加到你 AI 助手的 MCP 配置文件中（例如 `cline_mcp_settings.json` 或 `claude_desktop_config.json`）：

> **Windows 用户注意事项**：强烈建议指定 `--python 3.13`，以避免某些依赖项的编译问题。

```json
{
  "mcpServers": {
    "crawl": {
      "command": "uvx",
      "args": [
        "--python",
        "3.13",
        "crawl4ai-mcp-llm"
      ],
      "disabled": false,
      "autoApprove": [],
      "timeout": 600
    }
  }
}
```

### 重要提示：浏览器安装

抓取工具使用 Playwright 来处理动态内容。在配置完成后，你必须安装所需的浏览器：

```bash
uvx --from crawl4ai-mcp-llm playwright install chromium
```

## 🖥️ 使用方法

配置完成后，你可以通过让 AI 助手执行抓取来使用该工具。

### 在 Claude/Cline 中的使用示例

- **简单抓取**："你能抓取 example.com 网站并给我一个摘要吗？"
- **带选项抓取**："你能以深度 3 抓取 https://example.com 并包含外部链接吗？"
- **动态内容**："抓取这个 React 应用，并等待 `.main-content` 选择器加载完成。"
- **绕过保护**："抓取 example.com，但使用 'magic mode' 绕过反爬虫保护。"
- **定向提取**："抓取文档网站，但仅提取匹配 `h1, p.lead` CSS 选择器的内容。"

## 🛠️ 可用参数（MCP 工具）

`crawl` 工具接受以下参数：

| 参数 | 类型 | 说明 | 默认值 |
|-----------|------|-------------|---------------|
| `url` | string | 要抓取的 URL（必填） | - |
| `max_depth` | integer | 要跟随的链接深度（0-5）：0 = 仅起始页面，1 = 其链接，依此类推 | 2 |
| `max_pages` | integer | 要爬取的最大页面数（1-500） | 50 |
| `include_external` | boolean | 包含外部链接 | false |
| `wait_for_selector` | string | 在提取内容前等待的 CSS 选择器。适用于单页应用。 | None |
| `return_content` | boolean | 是否直接在 MCP 响应中返回提取的内容（如有必要会截断到 5 万字符）。 | true |
| `max_content_chars` | integer | 响应中返回内容的最大字符数 | 50000 |
| `output_file` | string | Markdown 文件名，始终保存在结果目录中 | 自动生成 |
| `overwrite` | boolean | 允许覆盖已存在的 `output_file` | false |
| `magic` | boolean | 启用 magic 模式以绕过反爬虫机制并模拟真实浏览器 | false |
| `css_selector` | string | 指定 CSS 选择器，仅从页面中提取目标元素 | None |
| `js_code` | string | 在提取前在页面上执行的自定义 JavaScript 代码 | None |
| `session_id` | string | 持久会话标识符，用于在请求之间保持 cookies 和浏览器状态 | None |
| `delay_before_return_html` | number | 提取 HTML 前等待的延迟秒数（适用于 JS 较多的页面） | None |

## 📄 许可证

本项目基于 MIT 许可证授权。

---

> 🏠 **源代码与文档**：[github.com/laurentvv/crawl4ai-mcp-llm](https://github.com/laurentvv/crawl4ai-mcp-llm)
