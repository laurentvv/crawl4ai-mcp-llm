import pytest

from crawl4ai_mcp_llm.crawler import crawl_and_output_to_markdown


@pytest.mark.anyio
@pytest.mark.parametrize("env_value", [None, "false"])
async def test_js_code_blocked(fake_crawler, monkeypatch, env_value):
    if env_value is not None:
        monkeypatch.setenv("CRAWL4AI_MCP_ALLOW_JS", env_value)

    result = await crawl_and_output_to_markdown("https://example.com", js_code="console.log('malicious code')")

    assert "Custom JavaScript execution is disabled" in result["error"]
    assert result["file_path"] is None
    assert fake_crawler.calls == []


@pytest.mark.anyio
@pytest.mark.parametrize("wait_for", ["js:() => true", "() => window.ready", "function(){return 1}", "x => x"])
async def test_js_wait_for_blocked(fake_crawler, wait_for):
    result = await crawl_and_output_to_markdown("https://example.com", wait_for_selector=wait_for)

    assert "JavaScript wait conditions are disabled" in result["error"]
    assert fake_crawler.calls == []


@pytest.mark.anyio
async def test_js_allowed_when_env_set_to_true(fake_crawler, monkeypatch):
    monkeypatch.setenv("CRAWL4AI_MCP_ALLOW_JS", "true")

    result = await crawl_and_output_to_markdown(
        "https://example.com", js_code="console.log('legit code')", wait_for_selector="js:() => true"
    )

    assert result["error"] is None
    config = fake_crawler.calls[0][1]
    assert config.js_code == "console.log('legit code')"
    assert config.wait_for == "js:() => true"
