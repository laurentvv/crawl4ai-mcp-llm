"""Crawl orchestration: runs crawl4ai and writes the results as Markdown."""

import logging
import math
import re
import time
from collections.abc import AsyncIterator, Iterable
from typing import Any, Literal, NamedTuple, NotRequired, TypedDict

import anyio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain

from .config import ALLOW_JS_ENV, Settings, get_settings
from .markdown import format_page
from .security import (
    SafeURLFilter,
    ValidationError,
    resolve_output_path,
    validate_url,
    validate_wait_for,
)
from .utils import generate_filename_from_url

logger = logging.getLogger(__name__)

# Kept for backward compatibility with code importing it from here.
CRAWL4AI_MCP_ALLOW_JS_ENV = ALLOW_JS_ENV

DEFAULT_MAX_CONTENT_CHARS = 50_000
UNTITLED_PAGE = "Untitled page"

# A title is treated as an error page only when one of its segments (split on
# " | ", " - ", " : " ...) is entirely an HTTP error phrase, e.g. "404 Not Found",
# "Page not found | Site" or "Error 403". Titles that merely contain these words
# ("Forbidden Planet", "Understanding HTTP 404 errors") are kept.
TITLE_SEPARATOR_REGEX = re.compile(r"\s+[|\-–—:·]\s+")
ERROR_TITLE_SEGMENT_REGEX = re.compile(
    r"^(?:(?:http\s+)?error\s*)?"
    r"(?P<code>40[134])?\s*[-:]?\s*"
    r"(?P<phrase>(?:page\s+)?not\s+found|forbidden|access\s+denied|unauthori[sz]ed)?"
    r"(?:\s+error)?[.!]?$",
    re.IGNORECASE,
)
# Bare nginx/apache error pages are tiny; longer texts mentioning them are articles.
MAX_SERVER_ERROR_PAGE_CHARS = 1_000
MAX_REASON_CHARS = 200

ErrorType = Literal["404", "403", "missing"]


class CrawlStats(TypedDict):
    successful_pages: int
    failed_pages: int
    not_found_pages: int
    forbidden_pages: int
    duration_seconds: float


class SkippedPage(TypedDict):
    url: str
    reason: str


class CrawlOutcome(TypedDict):
    error: str | None
    file_path: str | None
    stats: CrawlStats
    links: NotRequired[dict[str, list[dict[str, Any]]]]
    skipped: NotRequired[list[SkippedPage]]
    content: NotRequired[str]
    content_truncated: NotRequired[bool]
    timed_out: NotRequired[bool]


class PageCheck(NamedTuple):
    content: str | None
    error_type: ErrorType | None
    reason: str | None


def _empty_stats() -> CrawlStats:
    """Return a fresh empty stats dict (avoid duplication across error paths)."""
    return {
        "successful_pages": 0,
        "failed_pages": 0,
        "not_found_pages": 0,
        "forbidden_pages": 0,
        "duration_seconds": 0.0,
    }


def _error_outcome(message: str, stats: CrawlStats | None = None) -> CrawlOutcome:
    return {"error": message, "file_path": None, "stats": stats or _empty_stats()}


def _get_metadata(result: Any) -> dict[str, Any]:
    metadata = getattr(result, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _get_title(result: Any) -> str:
    title = _get_metadata(result).get("title")
    if title is None or not str(title).strip():
        return UNTITLED_PAGE
    return str(title).strip()


def classify_error_title(title: str) -> Literal["404", "403"] | None:
    """Return the HTTP error an error-page title stands for, if any."""
    for segment in TITLE_SEPARATOR_REGEX.split(title.strip()):
        match = ERROR_TITLE_SEGMENT_REGEX.match(segment.strip())
        if not match or not (match.group("code") or match.group("phrase")):
            continue
        code = match.group("code")
        phrase = (match.group("phrase") or "").lower()
        if code == "404" or (code is None and "not found" in phrase):
            return "404"
        return "403"
    return None


def _short_reason(message: object, max_chars: int = MAX_REASON_CHARS) -> str:
    """Keep the most informative line of a (possibly multi-line) crawl4ai error."""
    lines = [line.strip() for line in str(message or "").splitlines() if line.strip()]
    if not lines:
        return "no content"
    # crawl4ai prefixes errors with a generic "Unexpected error in ..." line;
    # the network error (e.g. "Page.goto: net::ERR_...") comes later.
    reason = next((line for line in lines if "net::" in line or "Error" in line), lines[0])
    return reason if len(reason) <= max_chars else reason[: max_chars - 3] + "..."


def _extract_page_content_and_errors(result: Any) -> PageCheck:
    """
    Extract text content from a result and check for common HTTP errors.
    Returns (content, error_type, reason) where error_type is '404', '403', 'missing' or None.
    """
    text_for_output = getattr(result, "markdown", None) or getattr(result, "text", None)
    if not text_for_output:
        return PageCheck(None, "missing", _short_reason(getattr(result, "error_message", None)))
    text_for_output = str(text_for_output)

    status_code = getattr(result, "status_code", None)
    if status_code == 404:
        return PageCheck(text_for_output, "404", "HTTP status 404")
    if status_code in (401, 403):
        return PageCheck(text_for_output, "403", f"HTTP status {status_code}")

    # Fallback: bare server error pages (nginx default pages)
    if len(text_for_output) <= MAX_SERVER_ERROR_PAGE_CHARS and "nginx" in text_for_output:
        if "404 Not Found" in text_for_output:
            return PageCheck(text_for_output, "404", "nginx error page")
        if "403 Forbidden" in text_for_output:
            return PageCheck(text_for_output, "403", "nginx error page")

    error_type = classify_error_title(_get_title(result))
    if error_type:
        return PageCheck(text_for_output, error_type, "error page title")

    return PageCheck(text_for_output, None, None)


def _format_markdown_page(result: Any, text_for_output: str) -> str:
    """Format a single crawl result into a Markdown string."""
    return format_page(
        url=getattr(result, "url", ""),
        title=_get_title(result),
        depth=_get_metadata(result).get("depth", "N/A"),
        text=text_for_output,
    )


class _LinkCollector:
    """Deduplicate internal and external links (by href) across results."""

    def __init__(self) -> None:
        self.links: dict[str, list[dict[str, Any]]] = {"internal": [], "external": []}
        self._seen: dict[str, set[str]] = {"internal": set(), "external": set()}

    def add(self, result: Any) -> None:
        result_links = getattr(result, "links", None)
        if not isinstance(result_links, dict):
            return
        for kind in ("internal", "external"):
            entries = result_links.get(kind)
            if not isinstance(entries, list):
                continue
            for link in entries:
                if not isinstance(link, dict):
                    continue
                href = link.get("href")
                if href and href not in self._seen[kind]:
                    self.links[kind].append(link)
                    self._seen[kind].add(href)


def _extract_unique_links(results: Iterable[Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract and deduplicate internal and external links from crawl results."""
    collector = _LinkCollector()
    for result in results:
        collector.add(result)
    return collector.links


async def _iterate(results: Any) -> AsyncIterator[Any]:
    """Iterate over batch (list) or streaming (async generator) crawl results."""
    if hasattr(results, "__aiter__"):
        async for result in results:
            yield result
    else:
        for result in results:
            yield result


async def _close_results(results: Any) -> None:
    aclose = getattr(results, "aclose", None)
    if aclose is None:
        return
    try:
        with anyio.CancelScope(shield=True):
            await aclose()
    except Exception:  # noqa: BLE001 - best effort cleanup of the crawl4ai generator
        logger.debug("Failed to close crawl result stream", exc_info=True)


async def results_to_markdown(
    results: Any,
    output_path: str,
    *,
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
    deadline: float = math.inf,
) -> CrawlOutcome:
    """
    Write crawl results (a list or an async stream) to a Markdown file.

    Pages are written as they arrive. The first ``max_content_chars`` characters
    are kept in memory so callers do not need to read the file back. When
    ``deadline`` (an ``anyio.current_time()`` value) is reached, the pages
    already written are kept and the outcome is flagged ``timed_out``.
    """
    stats = _empty_stats()
    skipped: list[SkippedPage] = []
    links = _LinkCollector()
    content_parts: list[str] = []
    content_len = 0
    truncated = False
    started = time.monotonic()

    try:
        async with await anyio.Path(output_path).open("w", encoding="utf-8") as md_file:
            with anyio.CancelScope(deadline=deadline) as scope:
                async for result in _iterate(results):
                    links.add(result)
                    url = str(getattr(result, "url", ""))
                    page = _extract_page_content_and_errors(result)

                    if page.error_type == "missing":
                        logger.info("No content found for %s (%s) - skipped", url, page.reason)
                        stats["failed_pages"] += 1
                        skipped.append({"url": url, "reason": page.reason or "no content"})
                        continue
                    if page.error_type in ("404", "403"):
                        logger.info("%s page detected (%s) and skipped: %s", page.error_type, page.reason, url)
                        if page.error_type == "404":
                            stats["not_found_pages"] += 1
                        else:
                            stats["forbidden_pages"] += 1
                        skipped.append({"url": url, "reason": f"{page.error_type} ({page.reason})"})
                        continue

                    content = page.content or ""
                    # Regex cleaning is CPU bound on large pages: keep the event loop free.
                    md_content = await anyio.to_thread.run_sync(_format_markdown_page, result, content)
                    await md_file.write(md_content)
                    stats["successful_pages"] += 1

                    if content_len < max_content_chars:
                        remaining = max_content_chars - content_len
                        content_parts.append(md_content[:remaining])
                        content_len += min(len(md_content), remaining)
                        truncated = truncated or len(md_content) > remaining
                    else:
                        truncated = True

            if scope.cancelled_caught:
                logger.warning("Crawl deadline reached, keeping %d page(s)", stats["successful_pages"])
                await _close_results(results)

        logger.info(
            "Valid pages processed: %d, error pages (403/404) skipped: %d",
            stats["successful_pages"],
            stats["not_found_pages"] + stats["forbidden_pages"],
        )
        stats["duration_seconds"] = time.monotonic() - started
        return {
            "error": None,
            "file_path": str(output_path),
            "stats": stats,
            "links": links.links,
            "skipped": skipped,
            "content": "".join(content_parts),
            "content_truncated": truncated,
            "timed_out": scope.cancelled_caught,
        }

    except OSError as e:
        logger.error("Error writing markdown file %s: %s", output_path, e)
        stats["duration_seconds"] = time.monotonic() - started
        return _error_outcome(f"Writing error: {e}", stats)


class CrawlerManager:
    """Lazily started ``AsyncWebCrawler`` shared across tool calls.

    Reusing one browser avoids a Chromium start-up per call and lets
    ``session_id`` keep cookies and page state between calls.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._crawler: AsyncWebCrawler | None = None
        self._lock: anyio.Lock | None = None
        self._limiter: anyio.CapacityLimiter | None = None

    @property
    def settings(self) -> Settings:
        return self._settings or get_settings()

    @property
    def limiter(self) -> anyio.CapacityLimiter:
        if self._limiter is None:
            self._limiter = anyio.CapacityLimiter(self.settings.max_concurrent_crawls)
        return self._limiter

    async def get(self) -> AsyncWebCrawler:
        if self._lock is None:
            self._lock = anyio.Lock()
        async with self._lock:
            if self._crawler is None:
                crawler = AsyncWebCrawler(config=BrowserConfig(verbose=self.settings.verbose))
                await crawler.start()
                self._crawler = crawler
            return self._crawler

    async def invalidate(self) -> None:
        """Drop the shared crawler (e.g. after a browser crash); restarted on next use."""
        await self.close()

    async def close(self) -> None:
        crawler, self._crawler = self._crawler, None
        if crawler is not None:
            try:
                with anyio.CancelScope(shield=True):
                    await crawler.close()
            except Exception:  # noqa: BLE001 - closing a broken browser must not mask the real error
                logger.debug("Error while closing the crawler", exc_info=True)


async def crawl_and_output_to_markdown(
    start_url: str,
    max_depth: int = 2,
    max_pages: int | None = None,
    include_external: bool = False,
    verbose: bool | None = None,
    output_file: str | None = None,
    wait_for_selector: str | None = None,
    magic: bool = False,
    css_selector: str | None = None,
    js_code: str | None = None,
    session_id: str | None = None,
    delay_before_return_html: float | None = None,
    *,
    overwrite: bool = False,
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
    settings: Settings | None = None,
    crawler_manager: CrawlerManager | None = None,
) -> CrawlOutcome:
    """
    Crawl a website and save the results to a Markdown file.

    ``max_depth`` follows crawl4ai semantics: 0 fetches only the start page,
    1 also follows the links found on it, and so on.
    """
    settings = settings or get_settings()
    if verbose is None:
        verbose = settings.verbose

    try:
        max_depth = int(max_depth)
        if max_depth < 0:
            raise ValidationError(f"max_depth must be >= 0 (got {max_depth}). Use 0 for a single page.")
        if max_pages is not None and int(max_pages) < 1:
            raise ValidationError(f"max_pages must be >= 1 (got {max_pages})")
        if js_code and not settings.allow_js:
            raise ValidationError(
                "Custom JavaScript execution is disabled for security reasons. "
                f"To enable it, set the environment variable {ALLOW_JS_ENV}=true"
            )
        wait_for = validate_wait_for(wait_for_selector, allow_js=settings.allow_js)
        start_url = await validate_url(start_url, allow_private_networks=settings.allow_private_networks)

        results_dir = settings.results_dir
        await anyio.Path(results_dir).mkdir(parents=True, exist_ok=True)
        if output_file:
            output_path = resolve_output_path(output_file, results_dir, overwrite=overwrite)
        else:
            output_path = results_dir / generate_filename_from_url(start_url)
    except ValidationError as e:
        return _error_outcome(str(e))
    except (TypeError, ValueError) as e:
        return _error_outcome(f"Invalid parameter: {e}")
    except OSError as e:
        return _error_outcome(f"Cannot prepare the results directory: {e}")

    strategy_kwargs: dict[str, Any] = {"max_depth": max_depth, "include_external": include_external}
    if max_pages is not None:
        strategy_kwargs["max_pages"] = int(max_pages)
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            filter_chain=FilterChain([SafeURLFilter(settings.allow_private_networks)]),
            **strategy_kwargs,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=verbose,
        magic=magic,
        stream=True,
    )
    if wait_for:
        config.wait_for = wait_for
    if css_selector:
        config.css_selector = css_selector
    if js_code:
        config.js_code = js_code
    if session_id:
        config.session_id = session_id
    if delay_before_return_html is not None:
        config.delay_before_return_html = delay_before_return_html

    timeout = settings.crawl_timeout
    try:
        if crawler_manager is None:
            async with AsyncWebCrawler(config=BrowserConfig(verbose=verbose)) as crawler:
                return await _run_crawl(crawler, start_url, config, output_path, timeout, max_content_chars)
        async with crawler_manager.limiter:
            crawler = await crawler_manager.get()
            return await _run_crawl(crawler, start_url, config, output_path, timeout, max_content_chars)
    except (OSError, TimeoutError, ConnectionError) as e:
        logger.warning("Crawling error for %s: %s", start_url, e)
        if crawler_manager is not None:
            await crawler_manager.invalidate()
        return _error_outcome(f"Crawling error: {e}")
    except Exception as e:
        logger.exception("Unexpected error while crawling %s", start_url)
        if crawler_manager is not None:
            await crawler_manager.invalidate()
        return _error_outcome(f"Crawling error: {e}")


async def _run_crawl(
    crawler: Any,
    start_url: str,
    config: CrawlerRunConfig,
    output_path: Any,
    timeout_seconds: float,
    max_content_chars: int,
) -> CrawlOutcome:
    deadline = anyio.current_time() + timeout_seconds
    with anyio.CancelScope(deadline=deadline) as scope:
        results = await crawler.arun(start_url, config=config)
    if scope.cancelled_caught:
        return _error_outcome(f"Crawl timed out after {timeout_seconds:g} seconds")

    outcome = await results_to_markdown(
        results, str(output_path), max_content_chars=max_content_chars, deadline=deadline
    )
    if outcome.get("timed_out"):
        logger.warning("Crawl of %s stopped after %g seconds (partial results kept)", start_url, timeout_seconds)
    return outcome
