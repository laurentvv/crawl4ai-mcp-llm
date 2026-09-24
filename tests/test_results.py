from types import SimpleNamespace
from unittest.mock import patch

import anyio
import pytest

from crawl4ai_mcp_llm.crawler import (
    CrawlerManager,
    _extract_page_content_and_errors,
    classify_error_title,
    crawl_and_output_to_markdown,
    results_to_markdown,
)


def make_result(i, error_type=None):
    if error_type == "missing":
        markdown, title = None, "No content"
    elif error_type == "404":
        markdown, title = "404 Not Found nginx", "404 Not Found"
    elif error_type == "403":
        markdown, title = "403 Forbidden nginx", "403 Forbidden"
    else:
        markdown, title = f"# Page {i}\nTest content.", f"Test Page {i}"
    return SimpleNamespace(
        url=f"https://example.com/page{i}",
        markdown=markdown,
        metadata={"title": title, "depth": 1},
        links={
            "internal": [{"href": f"https://example.com/page{i}/subpage"}],
            "external": [{"href": "https://external.com"}],
        },
    )


async def stream(results, delay=0):
    for result in results:
        if delay:
            await anyio.sleep(delay)
        yield result


@pytest.mark.anyio
async def test_results_to_markdown_success(tmp_path):
    output_path = tmp_path / "out.md"

    res = await results_to_markdown([make_result(1), make_result(2)], str(output_path))

    assert res["error"] is None
    assert res["file_path"] == str(output_path)
    assert res["stats"]["successful_pages"] == 2
    assert res["stats"]["failed_pages"] == 0
    assert res["timed_out"] is False
    content = output_path.read_text(encoding="utf-8")
    assert "# Test Page 1" in content and "# Test Page 2" in content
    assert res["content"] == content
    assert res["content_truncated"] is False
    assert len(res["links"]["internal"]) == 2
    assert len(res["links"]["external"]) == 1


@pytest.mark.anyio
async def test_results_to_markdown_accepts_streams(tmp_path):
    res = await results_to_markdown(stream([make_result(1), make_result(2)]), str(tmp_path / "out.md"))

    assert res["stats"]["successful_pages"] == 2


@pytest.mark.anyio
async def test_results_to_markdown_with_errors(tmp_path):
    results = [make_result(1), make_result(2, "missing"), make_result(3, "404"), make_result(4, "403")]

    res = await results_to_markdown(results, str(tmp_path / "out.md"))

    assert res["error"] is None
    assert res["stats"] == {**res["stats"], "successful_pages": 1, "failed_pages": 1}
    assert res["stats"]["not_found_pages"] == 1
    assert res["stats"]["forbidden_pages"] == 1
    assert [page["url"] for page in res["skipped"]] == [
        "https://example.com/page2",
        "https://example.com/page3",
        "https://example.com/page4",
    ]


@pytest.mark.anyio
async def test_results_to_markdown_truncates_returned_content(tmp_path):
    output_path = tmp_path / "out.md"

    res = await results_to_markdown([make_result(i) for i in range(5)], str(output_path), max_content_chars=100)

    assert len(res["content"]) == 100
    assert res["content_truncated"] is True
    assert res["stats"]["successful_pages"] == 5
    assert len(output_path.read_text(encoding="utf-8")) > 100


@pytest.mark.anyio
async def test_results_to_markdown_stops_at_deadline(tmp_path):
    deadline = anyio.current_time() + 0.15

    res = await results_to_markdown(
        stream([make_result(i) for i in range(50)], delay=0.05), str(tmp_path / "out.md"), deadline=deadline
    )

    assert res["error"] is None
    assert res["timed_out"] is True
    assert 0 < res["stats"]["successful_pages"] < 50


@pytest.mark.anyio
async def test_results_to_markdown_write_error():
    class FailingPath:
        def __init__(self, *args, **kwargs):
            pass

        async def open(self, *args, **kwargs):
            raise PermissionError("Permission denied")

    with patch("crawl4ai_mcp_llm.crawler.anyio.Path", side_effect=FailingPath):
        res = await results_to_markdown([make_result(1)], "out.md")

    assert res["error"] == "Writing error: Permission denied"
    assert res["file_path"] is None


@pytest.mark.parametrize(
    ("markdown", "title", "status_code", "expected"),
    [
        ("An error occurred: 404 Not Found nginx", "Normal Title", None, "404"),
        ("An error occurred: 403 Forbidden nginx", "Normal Title", None, "403"),
        ("Some content", "Page 404 Not Found", None, None),
        ("Some content", "404 Not Found", None, "404"),
        ("Some content", "Page not found | My Site", None, "404"),
        ("Some content", "Error 403", None, "403"),
        ("Some content", "Access Denied", None, "403"),
        ("Some content", "Great Page", 404, "404"),
        ("Some content", "Great Page", 401, "403"),
        ("Some content", "Great Page", 200, None),
        # Legitimate pages whose title merely mentions an error must be kept.
        ("Some content", "Forbidden Planet (1956) - Wikipedia", None, None),
        ("Some content", "Understanding HTTP 404 errors", None, None),
        ("Some content", "Page not found in legacy browsers: a guide", None, None),
        ("How to fix 404 Not Found in nginx " + "x" * 2000, "Fixing nginx", None, None),
    ],
)
def test_extract_page_content_and_errors(markdown, title, status_code, expected):
    result = SimpleNamespace(markdown=markdown, metadata={"title": title}, status_code=status_code)

    page = _extract_page_content_and_errors(result)

    assert page.content == markdown
    assert page.error_type == expected


def test_extract_page_content_and_errors_missing():
    result = SimpleNamespace(markdown=None, text=None, metadata=None, error_message="net::ERR_NAME_NOT_RESOLVED")

    page = _extract_page_content_and_errors(result)

    assert page == (None, "missing", "net::ERR_NAME_NOT_RESOLVED")


def test_missing_page_reason_prefers_network_error():
    message = (
        "Unexpected error in _crawl_web at line 778\nError: Failed on navigating ACS-GOTO:\n"
        "Page.goto: net::ERR_CONNECTION_REFUSED at https://example.com/\nCall log: ..."
    )
    result = SimpleNamespace(markdown=None, error_message=message)

    assert _extract_page_content_and_errors(result).reason == (
        "Page.goto: net::ERR_CONNECTION_REFUSED at https://example.com/"
    )


def test_classify_error_title_ignores_empty_title():
    assert classify_error_title("") is None


@pytest.mark.anyio
async def test_crawl_and_output_to_markdown_exception(fake_crawler):
    fake_crawler.error = Exception("Simulated crawl error")

    result = await crawl_and_output_to_markdown("https://example.com")

    assert result["error"] == "Crawling error: Simulated crawl error"
    assert result["file_path"] is None
    assert result["stats"]["successful_pages"] == 0
    assert result["stats"]["duration_seconds"] == 0


@pytest.mark.anyio
async def test_crawl_and_output_to_markdown_passes_parameters(fake_crawler, monkeypatch):
    monkeypatch.setenv("CRAWL4AI_MCP_ALLOW_JS", "true")

    result = await crawl_and_output_to_markdown(
        "https://example.com",
        max_depth=0,
        max_pages=3,
        magic=True,
        css_selector=".main",
        js_code="console.log('test');",
        session_id="test_session",
        delay_before_return_html=2.5,
        wait_for_selector="#app",
    )

    assert result["error"] is None
    ((url, config),) = fake_crawler.calls
    assert url == "https://example.com"
    assert config.magic is True
    assert config.stream is True
    assert config.css_selector == ".main"
    assert config.js_code == "console.log('test');"
    assert config.session_id == "test_session"
    assert config.delay_before_return_html == 2.5
    assert config.wait_for == "#app"
    assert config.deep_crawl_strategy.max_depth == 0
    assert config.deep_crawl_strategy.max_pages == 3


@pytest.mark.anyio
async def test_crawl_writes_into_results_dir(fake_crawler, results_dir):
    fake_crawler.results = [make_result(1)]

    result = await crawl_and_output_to_markdown("example.com", output_file="notes")

    assert result["error"] is None
    assert result["file_path"] == str(results_dir / "notes.md")
    assert fake_crawler.calls[0][0] == "https://example.com"


@pytest.mark.anyio
@pytest.mark.parametrize(("max_depth", "max_pages"), [(-1, None), ("abc", None), (1, 0)])
async def test_crawl_rejects_invalid_limits(fake_crawler, max_depth, max_pages):
    result = await crawl_and_output_to_markdown("https://example.com", max_depth=max_depth, max_pages=max_pages)

    assert result["error"]
    assert fake_crawler.calls == []


@pytest.mark.anyio
async def test_crawl_timeout(fake_crawler, monkeypatch):
    monkeypatch.setenv("CRAWL4AI_MCP_CRAWL_TIMEOUT", "0.1")

    async def slow_arun(url, config=None):
        await anyio.sleep(5)

    fake_crawler.arun = slow_arun

    result = await crawl_and_output_to_markdown("https://example.com")

    assert result["error"] == "Crawl timed out after 0.1 seconds"


@pytest.mark.anyio
async def test_crawler_manager_reuses_browser(fake_crawler):
    fake_crawler.results = [make_result(1)]
    manager = CrawlerManager()

    for _ in range(2):
        result = await crawl_and_output_to_markdown("https://example.com", crawler_manager=manager)
        assert result["error"] is None

    assert fake_crawler.started == 1
    await manager.close()
    assert fake_crawler.closed == 1


@pytest.mark.anyio
async def test_crawler_manager_restarts_after_failure(fake_crawler):
    manager = CrawlerManager()
    fake_crawler.error = RuntimeError("browser crashed")

    result = await crawl_and_output_to_markdown("https://example.com", crawler_manager=manager)

    assert result["error"] == "Crawling error: browser crashed"
    assert fake_crawler.closed == 1

    fake_crawler.error = None
    result = await crawl_and_output_to_markdown("https://example.com", crawler_manager=manager)
    assert result["error"] is None
    assert fake_crawler.started == 2
