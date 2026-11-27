"""MCP Apps UI resources, metadata constants, and structured payloads."""

from importlib import resources
from pathlib import Path
from typing import Any, Literal

from .crawler import CrawlOutcome
from .results import path_to_file_uri, relative_result_name, result_uri
from .security import is_safe_path

UI_MIME_TYPE = "text/html;profile=mcp-app"
CRAWL_CARD_FILENAME = "crawl-card.html"
EXPLORER_FILENAME = "explorer.html"
CRAWL_CARD_URI = f"ui://crawl4ai/{CRAWL_CARD_FILENAME}"
EXPLORER_URI = f"ui://crawl4ai/{EXPLORER_FILENAME}"

_ALLOWED_UI_FILES = frozenset({CRAWL_CARD_FILENAME, EXPLORER_FILENAME})

# Inline card rendered in the conversation stream for crawl / crawl_page.
CRAWL_CARD_META: dict[str, Any] = {
    "ui": {"resourceUri": CRAWL_CARD_URI},
}

# Side-panel (aux_pane) and full-page (global) explorer entrypoints.
EXPLORER_META: dict[str, Any] = {
    "ui": {"resourceUri": EXPLORER_URI},
    "com.google.antigravity/ui": {
        "entrypoints": [
            {"type": "aux_pane", "title": "Crawl4AI Explorer"},
            {"type": "global", "title": "Crawl4AI Explorer"},
        ]
    },
}

# Callable by the MCP App iframe only; hidden from the model on supporting hosts.
APP_ONLY_META: dict[str, Any] = {
    "ui": {"visibility": ["app"]},
}

UI_RESOURCE_META: dict[str, Any] = {
    "ui": {"prefersBorder": False},
}

# Keep trajectory-persisted CallToolResult payloads well below the 1 MiB host cap.
MAX_STRUCTURED_PREVIEW_CHARS = 24_000
MAX_STRUCTURED_LINKS = 100
MAX_STRUCTURED_SKIPPED = 100
MAX_EXPLORER_INITIAL_RESULTS = 200
MAX_RESULTS_PAGE_LIMIT = 500


def load_ui_html(filename: str, ui_dir: Path | None = None) -> str:
    """Load a bundled single-file MCP App HTML document.

    When ``ui_dir`` is provided (via ``CRAWL4AI_MCP_UI_DIR``), a matching file
    inside that directory overrides the packaged asset for fast local iteration.
    """
    if filename not in _ALLOWED_UI_FILES:
        raise FileNotFoundError(f"Unknown MCP App UI asset: {filename!r}")

    if ui_dir is not None:
        override = ui_dir / filename
        if is_safe_path(override, ui_dir) and override.is_file():
            return override.read_text(encoding="utf-8")

    asset = resources.files("crawl4ai_mcp_llm").joinpath("ui_assets", filename)
    if not asset.is_file():
        raise FileNotFoundError(f"Packaged MCP App UI asset is missing: {filename!r}")
    return asset.read_text(encoding="utf-8")


def _sample_links(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    sampled: list[dict[str, str]] = []
    for entry in entries[:MAX_STRUCTURED_LINKS]:
        href = entry.get("href")
        if not href:
            continue
        item: dict[str, str] = {"href": str(href)}
        text = entry.get("text")
        if text:
            item["text"] = str(text)[:160]
        sampled.append(item)
    return sampled


def build_crawl_structured_content(
    kind: Literal["crawl", "crawl_page"],
    url: str,
    outcome: CrawlOutcome,
    results_dir: Path | None = None,
) -> dict[str, Any]:
    """Build a bounded structured payload for the inline crawl card UI."""
    stats = outcome["stats"]
    if stats["successful_pages"] == 0:
        status = "empty"
    elif outcome.get("timed_out"):
        status = "partial"
    else:
        status = "completed"

    file_path = outcome.get("file_path")
    result_name = relative_result_name(file_path, results_dir) if file_path and results_dir else None
    res_uri = result_uri(file_path, results_dir) if file_path and results_dir else None

    raw_links = outcome.get("links") or {}
    internal_raw = raw_links.get("internal") or []
    external_raw = raw_links.get("external") or []
    skipped_raw = outcome.get("skipped") or []

    raw_content = outcome.get("content") or ""
    preview_truncated = len(raw_content) > MAX_STRUCTURED_PREVIEW_CHARS
    preview = raw_content[:MAX_STRUCTURED_PREVIEW_CHARS] if preview_truncated else raw_content

    return {
        "kind": kind,
        "status": status,
        "url": url,
        "file_path": file_path,
        "file_uri": path_to_file_uri(file_path),
        "result_name": result_name,
        "resource_uri": res_uri,
        "stats": dict(stats),
        "links": {
            "internal": _sample_links(internal_raw),
            "external": _sample_links(external_raw),
            "total_internal": len(internal_raw),
            "total_external": len(external_raw),
        },
        "skipped": list(skipped_raw[:MAX_STRUCTURED_SKIPPED]),
        "total_skipped": len(skipped_raw),
        "preview": preview,
        "preview_truncated": preview_truncated,
        "content_truncated": bool(outcome.get("content_truncated")),
        "timed_out": bool(outcome.get("timed_out")),
    }
