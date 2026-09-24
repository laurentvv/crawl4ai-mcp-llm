from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from crawl4ai_mcp_llm.crawler import _format_markdown_page

TEXT = "This is a [link](https://example.com) and some text."
FIXED_NOW = datetime(2023, 10, 27, 10, 0, 0)


@pytest.fixture(autouse=True)
def frozen_now():
    with patch("crawl4ai_mcp_llm.markdown.datetime") as mock_datetime:
        mock_datetime.now.return_value = FIXED_NOW
        yield


def make_result(**attrs):
    return SimpleNamespace(url="https://example.com", **attrs)


def test_format_markdown_page_nominal():
    result_str = _format_markdown_page(make_result(metadata={"title": "Example Page", "depth": 2}), TEXT)

    assert "# Example Page" in result_str
    assert "## URL\nhttps://example.com" in result_str
    assert "- Depth: 2" in result_str
    assert f"- Timestamp: {FIXED_NOW.isoformat()}" in result_str
    assert "This is a link and some text." in result_str
    assert "[link](https://example.com)" not in result_str


@pytest.mark.parametrize(
    "attrs", [{}, {"metadata": None}, {"metadata": {"title": None}}, {"metadata": {"title": "  "}}]
)
def test_format_markdown_page_missing_metadata(attrs):
    result_str = _format_markdown_page(make_result(**attrs), TEXT)

    assert "# Untitled page" in result_str
    assert "- Depth: N/A" in result_str


def test_format_markdown_page_partial_metadata():
    result_str = _format_markdown_page(make_result(metadata={"title": "Partial Page"}), TEXT)

    assert "# Partial Page" in result_str
    assert "- Depth: N/A" in result_str


def test_format_markdown_page_removes_images():
    result_str = _format_markdown_page(
        make_result(metadata={}), "Check this ![image](https://example.com/img.png) out."
    )

    assert "![image](https://example.com/img.png)" not in result_str
