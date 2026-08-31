import os
import re
import sys
import traceback
from datetime import datetime
import anyio

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

from .utils import (
    generate_filename_from_url,
    get_results_directory,
    is_safe_path,
    remove_links_from_markdown
)

# Environment variable to allow custom JavaScript execution
CRAWL4AI_MCP_ALLOW_JS_ENV = "CRAWL4AI_MCP_ALLOW_JS"

# Pre-compiled regex for performance optimization.
# Anchored to full title to avoid false positives on legitimate content
# (e.g. an article titled "Understanding HTTP 404 errors").
ERROR_INDICATORS_REGEX = re.compile(
    r"^(?:.*\s)?(?:404\s*[-:]?\s*not found|403\s*[-:]?\s*forbidden|not found|forbidden)(?:\s.*)?$",
    re.IGNORECASE,
)


def _empty_stats() -> dict:
    """Return a fresh empty stats dict (avoid duplication across error paths)."""
    return {
        "successful_pages": 0,
        "failed_pages": 0,
        "not_found_pages": 0,
        "forbidden_pages": 0,
        "duration_seconds": 0,
    }

async def crawl_and_output_to_markdown(
    start_url: str,
    max_depth: int = 2,
    max_pages: int | None = None,
    include_external: bool = False,
    verbose: bool = True,
    output_file: str = None,
    wait_for_selector: str = None,
    magic: bool = False,
    css_selector: str = None,
    js_code: str = None,
    session_id: str = None,
    delay_before_return_html: float = None,
) -> dict:
    """
    Crawl a website and save the results to a file
    """
    # Validate max_depth: 0 is ambiguous with BFSDeepCrawlStrategy and could
    # lead to unexpected crawling behavior. Enforce a minimum of 1 (single page).
    try:
        max_depth = int(max_depth)
    except (TypeError, ValueError):
        return {
            "error": f"max_depth must be an integer, got: {max_depth!r}",
            "file_path": None,
            "stats": _empty_stats(),
        }
    if max_depth < 1:
        return {
            "error": f"max_depth must be >= 1 (got {max_depth}). Use 1 for a single page.",
            "file_path": None,
            "stats": _empty_stats(),
        }

    results_dir = get_results_directory()

    # Generate a filename if not specified
    if not output_file:
        output_file = os.path.join(results_dir, generate_filename_from_url(start_url))
    else:
        # Ensure the provided output_file is within the results directory
        if not os.path.isabs(output_file):
            output_file = os.path.join(results_dir, output_file)

        if not is_safe_path(output_file, results_dir):
            return {
                "error": f"Invalid output path: {output_file}. Paths must be within {results_dir}",
                "file_path": None,
                "stats": _empty_stats(),
            }

    # Set basic configuration
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=include_external,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=verbose,
        magic=magic,
    )

    if wait_for_selector:
        config.wait_for = wait_for_selector
    if css_selector:
        config.css_selector = css_selector
    if js_code:
        if os.getenv(CRAWL4AI_MCP_ALLOW_JS_ENV, "false").lower() != "true":
            return {
                "error": f"Custom JavaScript execution is disabled for security reasons. To enable it, set the environment variable {CRAWL4AI_MCP_ALLOW_JS_ENV}=true",
                "file_path": None,
                "stats": _empty_stats(),
            }
        config.js_code = js_code
    if session_id:
        config.session_id = session_id
    if delay_before_return_html is not None:
        config.delay_before_return_html = delay_before_return_html

    try:
        async with AsyncWebCrawler() as crawler:
            results = await crawler.arun(start_url, config=config)
            print(f"Crawled {len(results)} pages in total", file=sys.stderr)
            
            # Create the parent folder if necessary
            await anyio.Path(os.path.dirname(os.path.abspath(output_file))).mkdir(parents=True, exist_ok=True)
            
            # Call results_to_markdown and get the result
            return await results_to_markdown(results, output_file)
    except Exception as e:
        print(f"Error during crawling: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return {
            "error": f"Crawling error: {str(e)}",
            "file_path": None,
            "stats": _empty_stats(),
        }

def _extract_page_content_and_errors(result) -> tuple[str | None, str | None]:
    """
    Extract text content from a result and check for common HTTP errors.
    Returns a tuple of (content, error_type) where error_type is '404', '403', or 'missing'.
    """
    text_for_output = getattr(result, "markdown", None) or getattr(result, "text", None)
    if not text_for_output:
        return None, "missing"
        
    status_code = getattr(result, "status_code", None)
    if status_code:
        if status_code == 404:
            return text_for_output, "404"
        elif status_code in (401, 403):
            return text_for_output, "403"

    # Fallback: Check if it's an error page (404 or 403)
    if ("404 Not Found" in text_for_output or "403 Forbidden" in text_for_output) and "nginx" in text_for_output:
        error_type = "404" if "404 Not Found" in text_for_output else "403"
        return text_for_output, error_type

    # Check metadata title for error indicators
    title = result.metadata.get("title", "Untitled page") if hasattr(result, "metadata") and result.metadata and result.metadata.get("title") is not None else "Untitled page"
    if title and ERROR_INDICATORS_REGEX.search(str(title)):
        error_type = "404" if "404" in str(title) or "Not Found" in str(title) else "403"
        # We still want to use the text but note it's an error
        return text_for_output, error_type

    return text_for_output, None

def _format_markdown_page(result, text_for_output: str) -> str:
    """
    Format a single crawl result into a Markdown string.
    """
    # Remove links from Markdown text
    clean_text = remove_links_from_markdown(text_for_output)

    # Structuring metadata
    metadata = {
        "depth": result.metadata.get("depth", "N/A") if hasattr(result, "metadata") else "N/A",
        "timestamp": datetime.now().isoformat(),
        "title": result.metadata.get("title", "Untitled page") if hasattr(result, "metadata") else "Untitled page",
    }

    # Formatted writing with literal template
    return f"""
# {metadata["title"]}

## URL
{result.url}

## Metadata
- Depth: {metadata["depth"]}
- Timestamp: {metadata["timestamp"]}

## Content
{clean_text}

---
"""

def _extract_unique_links(results: list) -> dict:
    """
    Extract and deduplicate internal and external links from crawl results.
    """
    links = {"internal": [], "external": []}
    seen_hrefs = {"internal": set(), "external": set()}

    for result in results:
        if hasattr(result, "links") and isinstance(result.links, dict):
            for k in ["internal", "external"]:
                if k in result.links:
                    for link in result.links[k]:
                        # avoid duplicates based on href
                        href = link.get('href')
                        if href and href not in seen_hrefs[k]:
                            links[k].append(link)
                            seen_hrefs[k].add(href)

    return links

async def results_to_markdown(results: list, output_path: str) -> dict:
    """
    Convert crawl results to a markdown file
    """
    stats = {
        "successful_pages": 0,
        "failed_pages": 0,
        "not_found_pages": 0,
        "forbidden_pages": 0,
        "start_time": datetime.now()
    }
    
    try:
        async with await anyio.Path(output_path).open("w", encoding="utf-8") as md_file:
            for result in results:
                text_for_output, error_type = _extract_page_content_and_errors(result)

                if error_type == "missing":
                    print(f"No content found for {result.url} - Skipped", file=sys.stderr)
                    stats["failed_pages"] += 1
                    continue
                elif error_type in ("404", "403"):
                    # For title errors, original code prints slightly differently
                    title = result.metadata.get("title", "Untitled page") if hasattr(result, "metadata") and result.metadata and result.metadata.get("title") is not None else "Untitled page"
                    if title and ERROR_INDICATORS_REGEX.search(str(title)):
                        print(f"Page with error title detected and skipped: {result.url}", file=sys.stderr)
                    else:
                        print(f"{error_type} page detected and skipped: {result.url}", file=sys.stderr)

                    if error_type == "404":
                        stats["not_found_pages"] += 1
                    else:
                        stats["forbidden_pages"] += 1
                    continue

                md_content = _format_markdown_page(result, text_for_output)
                await md_file.write(md_content)
                stats["successful_pages"] += 1
            
            # Display a summary at the end
            print(f"Valid pages processed: {stats['successful_pages']}", file=sys.stderr)
            print(f"Error pages (403/404) skipped: {stats['not_found_pages'] + stats['forbidden_pages']}", file=sys.stderr)
        
        links = _extract_unique_links(results)

        # Finalize statistics
        stats["end_time"] = datetime.now()
        stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).total_seconds()
        
        return {
            "file_path": output_path,
            "stats": stats,
            "links": links,
            "error": None
        }
    
    except Exception as e:
        print(f"Error writing markdown file: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return {
            "error": f"Writing error: {str(e)}",
            "file_path": None,
            "stats": stats
        }
