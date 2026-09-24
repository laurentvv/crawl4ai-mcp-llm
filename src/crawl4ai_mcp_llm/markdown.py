"""Markdown cleaning and page formatting for crawl results."""

import re
import uuid
from datetime import datetime

# Pre-compiled UI artifact regex
UI_ARTIFACTS_REGEX = re.compile(
    r"(?i)^\s*(?:Skip to main content|Search\.\.\.|Ctrl K|Copy page"
    r"|Was this page helpful\? YesNo|Powered by.*?Mintlify)\s*$",
    flags=re.MULTILINE,
)

# Pre-compiled regex patterns for markdown cleaning
EMPTY_HEADERS_REGEX = re.compile(r"#+\s*(?:\n|\r|\s)*\n")
EXCESSIVE_NEWLINES_REGEX = re.compile(r"\n{3,}")
CODE_BLOCK_REGEX = re.compile(r"```[\s\S]*?```")
IMAGE_REGEX = re.compile(r"!\[[^\]]*\]\([^)]+\)")
LINK_REGEX = re.compile(r"\[([^\]]+)\]\([^)]+\)")
EMPTY_LINES_REGEX = re.compile(r"\n\s*\n")
EXTRA_SPACES_REGEX = re.compile(r" {2,}")


def clean_ui_artifacts(text: str) -> str:
    """Remove common UI artifacts and empty markdown tags."""
    text = UI_ARTIFACTS_REGEX.sub("", text)

    # Remove empty markdown headers like "## "
    text = EMPTY_HEADERS_REGEX.sub("\n", text)

    # Clean up excessive newlines again
    text = EXCESSIVE_NEWLINES_REGEX.sub("\n\n", text)
    return text


def remove_links_from_markdown(markdown_text: str) -> str:
    """
    Remove links and images from markdown text while preserving text and code indentation.
    """
    # Identify and protect code blocks
    code_blocks: list[str] = []

    # Generate a unique prefix for this run
    block_prefix = f"__CODE_BLOCK_{uuid.uuid4().hex}_"

    # Function to replace code blocks with placeholders
    def save_code_block(match: re.Match[str]) -> str:
        code_blocks.append(match.group(0))
        return f"{block_prefix}{len(code_blocks) - 1}__"

    # Identify code blocks (between ``` and ```) and replace them with placeholders
    markdown_with_placeholders = CODE_BLOCK_REGEX.sub(save_code_block, markdown_text)

    # Completely remove images in ![text](url) format BEFORE links
    text_without_images = IMAGE_REGEX.sub("", markdown_with_placeholders)

    # Replace links in [text](url) format with just the text
    text_without_links = LINK_REGEX.sub(r"\1", text_without_images)

    # Clean UI artifacts
    text_cleaned = clean_ui_artifacts(text_without_links)

    # Remove lines containing only spaces
    text_without_empty_lines = EMPTY_LINES_REGEX.sub("\n\n", text_cleaned)

    # Remove blocks of consecutive spaces (but not in code blocks)
    text_without_extra_spaces = EXTRA_SPACES_REGEX.sub(" ", text_without_empty_lines)

    # Put the code blocks back in place
    restore_regex = re.compile(f"{block_prefix}(\\d+)__")

    def restore_code_block(match: re.Match[str]) -> str:
        return code_blocks[int(match.group(1))]

    return restore_regex.sub(restore_code_block, text_without_extra_spaces)


def format_page(url: str, title: str, depth: object, text: str) -> str:
    """Format a single crawled page as a Markdown section."""
    clean_text = remove_links_from_markdown(text)
    timestamp = datetime.now().isoformat()

    return f"""
# {title}

## URL
{url}

## Metadata
- Depth: {depth}
- Timestamp: {timestamp}

## Content
{clean_text}

---
"""
