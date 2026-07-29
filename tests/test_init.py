import pytest
from crawl4ai_mcp_llm.server import app

def test_app_exists():
    assert app.name == "mcp-web-crawler"

@pytest.mark.anyio
async def test_list_tools():
    tools = await app.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "crawl"
