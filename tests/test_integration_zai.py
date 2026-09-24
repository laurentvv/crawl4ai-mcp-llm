import anyio
import pytest

from crawl4ai_mcp_llm.crawler import crawl_and_output_to_markdown


@pytest.mark.anyio
@pytest.mark.integration
async def test_crawl_zai_docs():
    result = await crawl_and_output_to_markdown(
        start_url="https://docs.z.ai/devpack/overview",
        max_depth=1,
        max_pages=5,
        include_external=False,
    )

    assert result["error"] is None, f"Crawler returned an error: {result['error']}"
    file_path = result["file_path"]
    assert file_path is not None
    assert result["stats"]["successful_pages"] >= 1
    content = await anyio.Path(file_path).read_text(encoding="utf-8")
    assert content.strip(), "Generated markdown should not be empty"
