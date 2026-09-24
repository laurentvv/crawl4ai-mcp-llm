"""Progress reporting, single-page fetch, browser sessions and result resources."""

from types import SimpleNamespace

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from crawl4ai_mcp_llm import server
from crawl4ai_mcp_llm.crawler import CANCELLED_MARKER, CrawlerManager, crawl_and_output_to_markdown, results_to_markdown
from crawl4ai_mcp_llm.results import list_results, read_result, result_uri
from crawl4ai_mcp_llm.server import app, format_crawl_summary


def make_result(i, markdown=None):
    return SimpleNamespace(
        url=f"https://example.com/page{i}",
        markdown=markdown if markdown is not None else f"# Page {i}\nContent {i}.",
        metadata={"title": f"Page {i}", "depth": 1},
        links={},
    )


async def slow_stream(results, delay):
    for result in results:
        await anyio.sleep(delay)
        yield result


class FakeContext:
    """Minimal stand-in for mcp's Context outside of a real request."""

    def __init__(self):
        self.progress = []

    @property
    def request_context(self):
        raise ValueError("Context is not available outside of a request")

    async def report_progress(self, progress, total=None, message=None):
        self.progress.append((progress, total, message))


# --- 3.1 progress and streaming -------------------------------------------------


@pytest.mark.anyio
async def test_results_to_markdown_reports_progress_for_every_page(tmp_path):
    calls = []

    async def on_page(done, url):
        calls.append((done, url))

    results = [make_result(1), make_result(2, markdown=""), make_result(3)]
    await results_to_markdown(results, str(tmp_path / "out.md"), on_page=on_page)

    assert calls == [
        (1, "https://example.com/page1"),
        (2, "https://example.com/page2"),
        (3, "https://example.com/page3"),
    ]


@pytest.mark.anyio
async def test_progress_callback_errors_do_not_fail_the_crawl(tmp_path):
    async def broken(done, url):
        raise RuntimeError("client went away")

    res = await results_to_markdown([make_result(1)], str(tmp_path / "out.md"), on_page=broken)

    assert res["error"] is None
    assert res["stats"]["successful_pages"] == 1


@pytest.mark.anyio
async def test_cancellation_marks_partial_file(tmp_path):
    output_path = tmp_path / "out.md"

    with anyio.move_on_after(0.15):
        await results_to_markdown(slow_stream([make_result(i) for i in range(20)], 0.05), str(output_path))

    content = output_path.read_text(encoding="utf-8")
    assert "# Page 0" in content
    assert content.endswith(CANCELLED_MARKER)


@pytest.mark.anyio
async def test_crawl_tool_forwards_progress_to_client(monkeypatch):
    async def fake_crawl(url, **kwargs):
        await kwargs["on_page"](1, "https://example.com/a")
        await kwargs["on_page"](2, "https://example.com/b")
        return {
            "error": None,
            "file_path": None,
            "stats": {
                "successful_pages": 2,
                "failed_pages": 0,
                "not_found_pages": 0,
                "forbidden_pages": 0,
                "duration_seconds": 0.1,
            },
        }

    monkeypatch.setattr(server, "crawl_and_output_to_markdown", fake_crawl)
    ctx = FakeContext()

    await server.crawl(ctx=ctx, url="https://example.com", max_pages=10)

    assert ctx.progress == [
        (1, 10, "Processed https://example.com/a"),
        (2, 10, "Processed https://example.com/b"),
    ]


# --- 3.2 shared browser and sessions --------------------------------------------


@pytest.mark.anyio
async def test_sessions_are_tracked_and_closed(fake_crawler):
    manager = CrawlerManager()

    result = await crawl_and_output_to_markdown("https://example.com", session_id="login", crawler_manager=manager)

    assert result["error"] is None
    assert manager.sessions == ["login"]
    assert await manager.kill_session("login") is True
    assert fake_crawler.crawler_strategy.killed_sessions == ["login"]
    assert manager.sessions == []
    assert await manager.kill_session("login") is False


@pytest.mark.anyio
async def test_idle_sessions_expire(fake_crawler, monkeypatch):
    manager = CrawlerManager()
    await manager.get()
    manager.touch_session("old")
    manager.touch_session("recent")
    manager._sessions["old"] -= 3600

    assert await manager.expire_idle_sessions(ttl=1800) == ["old"]
    assert manager.sessions == ["recent"]
    assert fake_crawler.crawler_strategy.killed_sessions == ["old"]


@pytest.mark.anyio
async def test_expired_sessions_are_closed_before_next_crawl(fake_crawler, monkeypatch):
    monkeypatch.setenv("CRAWL4AI_MCP_SESSION_TTL", "60")
    manager = CrawlerManager()
    await crawl_and_output_to_markdown("https://example.com", session_id="s1", crawler_manager=manager)
    manager._sessions["s1"] -= 120

    await crawl_and_output_to_markdown("https://example.com", crawler_manager=manager)

    assert fake_crawler.crawler_strategy.killed_sessions == ["s1"]


@pytest.mark.anyio
async def test_close_session_tool(monkeypatch, fake_crawler):
    manager = CrawlerManager()
    monkeypatch.setattr(server, "crawler_manager", manager)
    await manager.get()
    manager.touch_session("abc")

    closed = await app.call_tool("close_session", {"session_id": "abc"})
    missing = await app.call_tool("close_session", {"session_id": "abc"})

    assert closed.content[0].text == "Session 'abc' closed."
    assert missing.content[0].text == "No open session named 'abc'."


# --- 3.3 crawl_page and result resources ----------------------------------------


@pytest.mark.anyio
async def test_crawl_without_file(fake_crawler, results_dir):
    fake_crawler.results = [make_result(1)]

    result = await crawl_and_output_to_markdown("https://example.com", write_file=False)

    assert result["error"] is None
    assert result["file_path"] is None
    assert "# Page 1" in result["content"]
    assert not results_dir.exists() or not any(results_dir.iterdir())


@pytest.mark.anyio
async def test_crawl_page_tool(monkeypatch, fake_crawler, results_dir):
    monkeypatch.setattr(server, "crawler_manager", CrawlerManager())
    fake_crawler.results = [make_result(1)]

    result = await app.call_tool("crawl_page", {"url": "https://example.com/page1", "css_selector": "main"})

    text = result.content[0].text
    assert result.is_error is False
    assert "<untrusted-web-content>" in text and "# Page 1" in text
    ((url, config),) = fake_crawler.calls
    assert config.deep_crawl_strategy.max_depth == 0
    assert config.deep_crawl_strategy.max_pages == 1
    assert config.css_selector == "main"
    assert not results_dir.exists() or not any(results_dir.iterdir())


@pytest.mark.anyio
async def test_crawl_page_tool_reports_unreadable_page(monkeypatch, fake_crawler):
    monkeypatch.setattr(server, "crawler_manager", CrawlerManager())
    fake_crawler.results = [SimpleNamespace(url="https://example.com", markdown=None, error_message="net::ERR_FAILED")]

    with pytest.raises(ToolError, match="Could not extract .*net::ERR_FAILED"):
        await app.call_tool("crawl_page", {"url": "https://example.com"})


@pytest.fixture
def saved_results(results_dir):
    (results_dir / "sub").mkdir(parents=True)
    (results_dir / "a.md").write_text("\n# A\n\n## URL\nhttps://a.example/\n\n## Content\nAlpha\n", encoding="utf-8")
    (results_dir / "sub" / "b.md").write_text("# B\n\n## URL\nhttps://b.example/x\n", encoding="utf-8")
    (results_dir / "notes.txt").write_text("not a result", encoding="utf-8")
    return results_dir


@pytest.mark.anyio
async def test_list_results(saved_results):
    entries = await list_results(saved_results)

    assert sorted(entry["uri"] for entry in entries) == ["crawl://results/a.md", "crawl://results/sub/b.md"]
    assert {entry["name"]: entry["source_url"] for entry in entries} == {
        "a.md": "https://a.example/",
        "sub/b.md": "https://b.example/x",
    }


@pytest.mark.anyio
async def test_list_results_reads_windows_line_endings(results_dir):
    results_dir.mkdir(parents=True)
    (results_dir / "crlf.md").write_bytes(b"\r\n# C\r\n\r\n## URL\r\nhttps://c.example/\r\n")

    (entry,) = await list_results(results_dir)

    assert entry["source_url"] == "https://c.example/"


@pytest.mark.anyio
async def test_list_results_missing_dir(tmp_path):
    assert await list_results(tmp_path / "nope") == []


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["../secret.md", "/etc/passwd", "notes.txt", "missing.md", ""])
async def test_read_result_rejects_invalid_paths(saved_results, path):
    (saved_results.parent / "secret.md").write_text("secret", encoding="utf-8")

    with pytest.raises(LookupError):
        await read_result(path, saved_results)


@pytest.mark.anyio
async def test_result_resources_through_mcp(saved_results):
    templates = await app.list_resource_templates()
    resources = await app.list_resources()
    assert [t.uri_template for t in templates] == ["crawl://results/{+path}"]
    assert [str(r.uri) for r in resources] == ["crawl://results"]

    listing = list(await app.read_resource("crawl://results"))
    assert "crawl://results/sub/b.md" in listing[0].content

    content = list(await app.read_resource("crawl://results/sub/b.md"))
    assert content[0].content.startswith("# B")

    for uri in ["crawl://results/../secret.md", "crawl://results/missing.md"]:
        with pytest.raises(Exception):  # noqa: B017 - SDK security error or ResourceError
            await app.read_resource(uri)


def test_summary_links_the_result_resource(results_dir):
    file_path = results_dir / "crawl.md"
    outcome = {
        "error": None,
        "file_path": str(file_path),
        "stats": {
            "successful_pages": 1,
            "failed_pages": 0,
            "not_found_pages": 0,
            "forbidden_pages": 0,
            "duration_seconds": 1.0,
        },
        "content": "x" * 10,
        "content_truncated": True,
    }

    text = format_crawl_summary("https://example.com", outcome, True, results_dir)

    assert "- Resource: crawl://results/crawl.md" in text
    assert "read the resource crawl://results/crawl.md for the full text" in text
    assert result_uri("/elsewhere/file.md", results_dir) is None
