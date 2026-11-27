"""Tests for MCP Apps metadata, UI resources, structured payloads, and app-only tools."""

import os

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from crawl4ai_mcp_llm import server
from crawl4ai_mcp_llm.crawler import CrawlerManager
from crawl4ai_mcp_llm.server import app
from crawl4ai_mcp_llm.ui import (
    CRAWL_CARD_FILENAME,
    CRAWL_CARD_URI,
    EXPLORER_URI,
    MAX_STRUCTURED_PREVIEW_CHARS,
    UI_MIME_TYPE,
    build_crawl_structured_content,
    load_ui_html,
)


@pytest.mark.anyio
async def test_tools_expose_mcp_app_metadata():
    tools = {tool.name: tool for tool in await app.list_tools()}

    assert tools["crawl"].meta == {"ui": {"resourceUri": CRAWL_CARD_URI}}
    assert tools["crawl_page"].meta == {"ui": {"resourceUri": CRAWL_CARD_URI}}
    assert tools["open_crawl_explorer"].meta == {
        "ui": {"resourceUri": EXPLORER_URI},
        "com.google.antigravity/ui": {
            "entrypoints": [
                {"type": "aux_pane", "title": "Crawl4AI Explorer"},
                {"type": "global", "title": "Crawl4AI Explorer"},
            ]
        },
    }
    assert tools["app_list_results"].meta == {"ui": {"visibility": ["app"]}}
    assert tools["app_read_result"].meta == {"ui": {"visibility": ["app"]}}
    assert tools["close_session"].meta is None


@pytest.mark.anyio
async def test_ui_resources_return_bundled_singlefile_html():
    resources = {str(r.uri): r for r in await app.list_resources()}

    for uri in (CRAWL_CARD_URI, EXPLORER_URI):
        assert uri in resources
        assert resources[uri].mime_type == UI_MIME_TYPE
        assert resources[uri].meta == {"ui": {"prefersBorder": False}}

        contents = list(await app.read_resource(uri))
        html = contents[0].content
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html or "<!doctype html>" in html
        assert len(html.encode("utf-8")) < 10 * 1024 * 1024


@pytest.mark.anyio
async def test_ui_dir_override_and_unknown_asset_rejection(tmp_path, monkeypatch):
    custom_html = "<!DOCTYPE html><html><body>custom-override</body></html>"
    (tmp_path / CRAWL_CARD_FILENAME).write_text(custom_html, encoding="utf-8")
    monkeypatch.setenv("CRAWL4AI_MCP_UI_DIR", str(tmp_path))

    contents = list(await app.read_resource(CRAWL_CARD_URI))
    assert contents[0].content == custom_html

    with pytest.raises(FileNotFoundError):
        load_ui_html("../secret.html", tmp_path)


def test_build_crawl_structured_content_bounds_preview_and_links(tmp_path):
    result_file = tmp_path / "site.md"
    outcome = {
        "error": None,
        "file_path": str(result_file),
        "stats": {
            "successful_pages": 3,
            "failed_pages": 0,
            "not_found_pages": 1,
            "forbidden_pages": 0,
            "duration_seconds": 2.4,
        },
        "links": {
            "internal": [{"href": f"https://example.com/{i}", "text": f"Link {i}"} for i in range(150)],
            "external": [{"href": "https://other.example/"}],
        },
        "skipped": [{"url": f"https://example.com/miss/{i}", "reason": "404"} for i in range(120)],
        "content": "a" * (MAX_STRUCTURED_PREVIEW_CHARS + 500),
        "content_truncated": False,
        "timed_out": False,
    }

    structured = build_crawl_structured_content("crawl", "https://example.com", outcome, tmp_path)

    assert structured["kind"] == "crawl"
    assert structured["status"] == "completed"
    assert structured["result_name"] == "site.md"
    assert structured["resource_uri"] == "crawl://results/site.md"
    assert structured["file_uri"].startswith("file://")
    assert structured["preview_truncated"] is True
    assert len(structured["preview"]) == MAX_STRUCTURED_PREVIEW_CHARS
    assert len(structured["links"]["internal"]) == 100
    assert structured["links"]["total_internal"] == 150
    assert len(structured["skipped"]) == 100
    assert structured["total_skipped"] == 120


@pytest.mark.anyio
async def test_crawl_and_crawl_page_return_structured_content(monkeypatch, results_dir):
    results_dir.mkdir(parents=True, exist_ok=True)
    saved = results_dir / "example.md"
    saved.write_text("# Hello\nWorld", encoding="utf-8")

    async def fake_crawl(url, **kwargs):
        return {
            "error": None,
            "file_path": str(saved) if kwargs.get("write_file", True) else None,
            "stats": {
                "successful_pages": 1,
                "failed_pages": 0,
                "not_found_pages": 0,
                "forbidden_pages": 0,
                "duration_seconds": 0.4,
            },
            "links": {"internal": [{"href": "https://example.com/docs"}], "external": []},
            "skipped": [],
            "content": "# Hello\nWorld",
            "content_truncated": False,
            "timed_out": False,
        }

    monkeypatch.setattr(server, "crawl_and_output_to_markdown", fake_crawl)

    crawl_res = await app.call_tool("crawl", {"url": "https://example.com"})
    assert crawl_res.is_error is False
    assert "Crawl completed successfully" in crawl_res.content[0].text
    assert crawl_res.structured_content["kind"] == "crawl"
    assert crawl_res.structured_content["resource_uri"] == "crawl://results/example.md"

    page_res = await app.call_tool("crawl_page", {"url": "https://example.com"})
    assert page_res.is_error is False
    assert "## Page fetched" in page_res.content[0].text
    assert page_res.structured_content["kind"] == "crawl_page"
    assert page_res.structured_content["preview"] == "# Hello\nWorld"


@pytest.mark.anyio
async def test_open_crawl_explorer_handles_empty_and_targeted_args(monkeypatch, results_dir):
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "docs.md").write_text("# Docs\n\n## URL\nhttps://docs.example/\n", encoding="utf-8")
    manager = CrawlerManager()
    manager.touch_session("auth-session")
    monkeypatch.setattr(server, "crawler_manager", manager)

    # Manual launch from "+" menu or sidebar always sends {}
    empty_res = await app.call_tool("open_crawl_explorer", {})
    assert empty_res.is_error is False
    assert "Saved results: 1" in empty_res.content[0].text
    assert empty_res.structured_content["kind"] == "explorer"
    assert empty_res.structured_content["sessions"] == ["auth-session"]
    assert empty_res.structured_content["results"][0]["name"] == "docs.md"
    assert empty_res.structured_content["results"][0]["file_uri"].startswith("file://")

    # Agent-driven update
    targeted = await app.call_tool(
        "open_crawl_explorer",
        {"selected_result": "docs.md", "initial_url": "https://docs.example/new"},
    )
    assert targeted.structured_content["selected_result"] == "docs.md"
    assert targeted.structured_content["initial_url"] == "https://docs.example/new"


@pytest.mark.anyio
async def test_app_only_result_helpers_and_path_safety(monkeypatch, results_dir):
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "guide.md").write_text("# Guide\nFull markdown body.", encoding="utf-8")
    (results_dir.parent / "secret.md").write_text("top secret", encoding="utf-8")
    monkeypatch.setattr(server, "crawler_manager", CrawlerManager())

    listed = await app.call_tool("app_list_results", {})
    assert listed.is_error is False
    assert [r["name"] for r in listed.structured_content["results"]] == ["guide.md"]

    loaded = await app.call_tool("app_read_result", {"name": "guide.md"})
    assert loaded.is_error is False
    assert loaded.structured_content["content"] == "# Guide\nFull markdown body."
    assert loaded.structured_content["uri"] == "crawl://results/guide.md"
    assert loaded.structured_content["file_uri"].startswith("file://")

    for bad_name in ("../secret.md", "missing.md", "notes.txt"):
        with pytest.raises(ToolError):
            await app.call_tool("app_read_result", {"name": bad_name})


@pytest.mark.anyio
async def test_explorer_and_app_list_results_paginate_and_filter(monkeypatch, results_dir):
    results_dir.mkdir(parents=True, exist_ok=True)
    for idx, (name, url) in enumerate(
        [
            ("alpha.md", "https://alpha.example/docs"),
            ("beta.md", "https://beta.example/api"),
            ("gamma.md", "https://gamma.example/docs"),
        ]
    ):
        path = results_dir / name
        path.write_text(f"# {name}\n\n## URL\n{url}\n", encoding="utf-8")
        # Ensure deterministic newest-first ordering across filesystems.
        mtime = 1_700_000_000 + idx * 10
        path.touch()
        os.utime(path, (mtime, mtime))

    monkeypatch.setattr(server, "crawler_manager", CrawlerManager())
    monkeypatch.setattr(server, "MAX_EXPLORER_INITIAL_RESULTS", 2)

    explorer = await app.call_tool("open_crawl_explorer", {})
    assert len(explorer.structured_content["results"]) == 2
    assert explorer.structured_content["total_results"] == 3
    assert explorer.structured_content["has_more"] is True
    assert explorer.structured_content["offset"] == 0
    assert explorer.structured_content["limit"] == 2

    page1 = await app.call_tool("app_list_results", {"offset": 0, "limit": 2})
    assert [r["name"] for r in page1.structured_content["results"]] == ["gamma.md", "beta.md"]
    assert page1.structured_content["has_more"] is True
    assert page1.structured_content["total_results"] == 3
    assert page1.structured_content["total_all"] == 3

    page2 = await app.call_tool("app_list_results", {"offset": 2, "limit": 2})
    assert [r["name"] for r in page2.structured_content["results"]] == ["alpha.md"]
    assert page2.structured_content["has_more"] is False

    filtered = await app.call_tool("app_list_results", {"query": "/docs"})
    assert [r["name"] for r in filtered.structured_content["results"]] == ["gamma.md", "alpha.md"]
    assert filtered.structured_content["total_results"] == 2
    assert filtered.structured_content["total_all"] == 3
    assert filtered.structured_content["has_more"] is False
