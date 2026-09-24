import pytest

from crawl4ai_mcp_llm.markdown import clean_ui_artifacts


@pytest.mark.parametrize(
    "text",
    [
        "Skip to main content",
        "  Search...  ",
        "ctrl k",
        "Copy page",
        "Was this page helpful? YesNo",
        "Powered by Mintlify",
    ],
)
def test_remove_ui_strings(text):
    assert clean_ui_artifacts(text).strip() == ""


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# \n", "\n"),
        ("## \r\n", "\n"),
        ("###    \n", "\n"),
        ("#### \nMore text", "\nMore text"),
        ("# Header with text\n", "# Header with text\n"),
    ],
)
def test_remove_empty_headers(text, expected):
    assert clean_ui_artifacts(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Text\n\n\nMore text", "Text\n\nMore text"),
        ("Text\n\n\n\n\nMore text", "Text\n\nMore text"),
        ("Text\n\nMore text", "Text\n\nMore text"),
    ],
)
def test_collapse_newlines(text, expected):
    assert clean_ui_artifacts(text) == expected


def test_preserve_content():
    content = """
# Real Header
This is a paragraph.
- List item 1
- List item 2

```python
def hello():
    print("world")
```

Another paragraph.
"""
    assert clean_ui_artifacts(content) == content


def test_combined_artifacts():
    text = "#\nSkip to main content\n## Real Header\n\n\nSearch...\n\n\nText here.\n\n\n"
    assert clean_ui_artifacts(text) == "\n## Real Header\n\nText here.\n\n"
