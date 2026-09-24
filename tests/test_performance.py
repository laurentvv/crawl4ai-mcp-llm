import re

from crawl4ai_mcp_llm.markdown import clean_ui_artifacts, remove_links_from_markdown


def remove_links_reference(markdown_text):
    """Straightforward reference implementation used to check equivalence."""
    code_blocks = []

    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    text = re.sub(r"```[\s\S]*?```", save_code_block, markdown_text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = clean_ui_artifacts(text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    for i, code_block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", code_block)
    return text


def test_matches_reference_implementation():
    text = ""
    for i in range(200):
        text += f"Some ![image](img{i}.jpg) and [link text {i}](http://example.com/{i}) here.  \n\n"
        text += f"```python\nprint('Hello world {i}')\nfor j in range(10):\n    pass\n```\n"

    assert remove_links_from_markdown(text) == remove_links_reference(text)


def test_code_blocks_are_preserved():
    text = "See [docs](http://x).\n```\n[not a link](kept)  two  spaces\n```\n"
    result = remove_links_from_markdown(text)
    assert "See docs." in result
    assert "[not a link](kept)  two  spaces" in result
