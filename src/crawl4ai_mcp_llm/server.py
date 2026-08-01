import sys
import traceback
import anyio
from mcp.server import MCPServer

from .crawler import crawl_and_output_to_markdown, CRAWL4AI_MCP_ALLOW_JS_ENV
from .utils import sanitize_for_display

app = MCPServer("mcp-web-crawler", version="0.1.4")

@app.tool()
async def crawl(
    url: str,
    max_depth: int = 2,
    include_external: bool = False,
    verbose: bool = True,
    output_file: str | None = None,
    wait_for_selector: str | None = None,
    return_content: bool = True,
    magic: bool = False,
    css_selector: str | None = None,
    js_code: str | None = None,
    session_id: str | None = None,
    delay_before_return_html: float | None = None,
) -> str:
    f"""Crawls a website and saves its content as structured markdown to a file.

    ⚠️ PERFORMANCE WARNING: This tool can take from 30 seconds to several minutes
    depending on the site. Heavy/SPA sites (React, Next.js, Mintlify), high
    `max_depth`, and the first crawl of a session (Playwright browser startup)
    are especially slow. The MCP client timeout should be set generously
    (e.g. 600000 ms / 10 min).

    TIPS to speed up crawls:
    - Use `css_selector` to extract only the relevant content (e.g. 'main', 'article').
    - Use `wait_for_selector` for single-page applications.
    - Lower `max_depth` (1 = single page) when you don't need recursive crawling.
    - Warn the user before launching a crawl that it may take a while.
    - Custom JavaScript code (js_code) requires {CRAWL4AI_MCP_ALLOW_JS_ENV}=true environment variable.
    """
    try:
        result = await crawl_and_output_to_markdown(
            url,
            max_depth=max_depth,
            include_external=include_external,
            verbose=verbose,
            output_file=output_file,
            wait_for_selector=wait_for_selector,
            magic=magic,
            css_selector=css_selector,
            js_code=js_code,
            session_id=session_id,
            delay_before_return_html=delay_before_return_html,
        )

        if result["error"]:
            return f"Error: {result['error']}"

        file_path = result["file_path"]
        stats = result["stats"]

        links_summary = ""
        if "links" in result:
            internal_links = [link.get("href") for link in result["links"].get("internal", [])[:20]]
            external_links = [link.get("href") for link in result["links"].get("external", [])[:20]]
            if internal_links or external_links:
                links_summary = "\n## Extracted Links (Sample)"
                if internal_links:
                    links_summary += "\n### Internal Links\n- " + "\n- ".join(internal_links)
                if external_links:
                    links_summary += "\n### External Links\n- " + "\n- ".join(external_links)
                links_summary += "\n"

        content_text = ""
        if return_content and file_path:
            try:
                async with await anyio.Path(file_path).open("r", encoding="utf-8") as f:
                    content_text = await f.read()

                max_chars = 50000
                if len(content_text) > max_chars:
                    content_text = content_text[:max_chars] + "\n\n...[Content truncated due to length]..."

                content_text = f"\n\n## Extracted Content\n\n{content_text}"
            except Exception as e:
                print(f"Failed to read content for return: {e}", file=sys.stderr)

        summary = f"""
## Crawl completed successfully
- URL: {url}
- Result file: {file_path}
- Duration: {stats["duration_seconds"]:.2f} seconds
- Pages processed: {stats["successful_pages"]} successful, {stats["failed_pages"]} failed, 
  {stats.get("not_found_pages", 0)} not found (404), {stats.get("forbidden_pages", 0)} access forbidden (403)
{links_summary}
You can view the full results in the file: {file_path}
(Results are now stored in the 'crawl_results' folder of your project)
{content_text}
        """
        return summary
    except Exception as e:
        print(f"Error in crawl_tool: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return f"Error: {sanitize_for_display(str(e))}"

