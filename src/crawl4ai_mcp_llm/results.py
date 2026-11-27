"""Access to saved crawl results, exposed as MCP resources."""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

import anyio

from .security import is_safe_path

RESULTS_URI = "crawl://results"
RESULT_URI_PREFIX = f"{RESULTS_URI}/"
_SOURCE_URL_REGEX = re.compile(r"^## URL\r?\n(\S+)", re.MULTILINE)
_HEADER_BYTES = 4096
_MAX_SOURCE_URL_CACHE = 4096
# Cache source_url by (resolved_path, mtime_ns, size_bytes) so large result folders
# do not re-open every unchanged file on search or pagination calls.
_SOURCE_URL_CACHE: dict[tuple[str, int, int], str | None] = {}


class ResultFile(TypedDict):
    uri: str
    name: str
    size_bytes: int
    modified: str
    source_url: str | None


class SearchMatch(TypedDict):
    uri: str
    name: str
    file_uri: str | None
    size_bytes: int
    modified: str
    source_url: str | None
    line: int
    snippet: str
    match_count: int


class ResultNotFoundError(LookupError):
    """Raised when a result path is invalid or does not exist."""


def relative_result_name(file_path: str | Path, results_dir: Path) -> str | None:
    """Return the POSIX path of a saved result relative to ``results_dir``, or None."""
    path = Path(file_path)
    if not is_safe_path(path, results_dir):
        return None
    return path.resolve().relative_to(results_dir.resolve()).as_posix()


def result_uri(file_path: str | Path, results_dir: Path) -> str | None:
    """Return the resource URI of a saved result, or None if it is outside ``results_dir``."""
    relative = relative_result_name(file_path, results_dir)
    return RESULT_URI_PREFIX + relative if relative is not None else None


def result_file_uri(relative_path: str, results_dir: Path) -> str:
    """Return the ``file://`` URI of a validated result inside ``results_dir``."""
    return _resolve_result_path(relative_path, results_dir).resolve().as_uri()


def path_to_file_uri(file_path: str | Path | None) -> str | None:
    """Convert an existing or target filesystem path to a ``file://`` URI."""
    if not file_path:
        return None
    try:
        return Path(file_path).resolve().as_uri()
    except ValueError:
        return None


def _resolve_result_path(relative_path: str, results_dir: Path) -> Path:
    candidate = results_dir / relative_path
    if (
        not relative_path
        or Path(relative_path).is_absolute()
        or candidate.suffix.lower() != ".md"
        or not is_safe_path(candidate, results_dir)
    ):
        raise ResultNotFoundError(f"Invalid result path: {relative_path!r}")
    return candidate


async def read_result(relative_path: str, results_dir: Path) -> str:
    """Read a saved result by its path relative to ``results_dir``."""
    path = anyio.Path(_resolve_result_path(relative_path, results_dir))
    if not await path.is_file():
        raise ResultNotFoundError(f"No crawl result named {relative_path!r}")
    return await path.read_text(encoding="utf-8")


def _read_source_url_cached(path: Path, mtime_ns: int, size_bytes: int) -> str | None:
    key = (str(path), mtime_ns, size_bytes)
    if key in _SOURCE_URL_CACHE:
        return _SOURCE_URL_CACHE[key]
    try:
        with path.open("rb") as handle:
            header = handle.read(_HEADER_BYTES).decode("utf-8", errors="ignore")
    except OSError:
        return None
    match = _SOURCE_URL_REGEX.search(header)
    url = match.group(1) if match else None
    if len(_SOURCE_URL_CACHE) >= _MAX_SOURCE_URL_CACHE:
        _SOURCE_URL_CACHE.clear()
    _SOURCE_URL_CACHE[key] = url
    return url


def _list_results_sync(results_dir: Path) -> list[ResultFile]:
    if not results_dir.is_dir():
        return []
    entries: list[tuple[float, ResultFile]] = []
    for path in results_dir.rglob("*.md"):
        try:
            if not path.is_file() or not is_safe_path(path, results_dir):
                continue
            stat = path.stat()
        except OSError:
            continue
        relative = path.relative_to(results_dir).as_posix()
        entries.append(
            (
                stat.st_mtime,
                {
                    "uri": RESULT_URI_PREFIX + relative,
                    "name": relative,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    "source_url": _read_source_url_cached(path, stat.st_mtime_ns, stat.st_size),
                },
            )
        )
    entries.sort(key=lambda entry: entry[0], reverse=True)
    return [entry for _, entry in entries]


async def list_results(results_dir: Path) -> list[ResultFile]:
    """List saved results (newest first) with the URL of their first page."""
    return await anyio.to_thread.run_sync(_list_results_sync, results_dir)


_MAX_SEARCH_FILE_BYTES = 2 * 1024 * 1024
_SNIPPET_RADIUS = 90


def _build_snippet(text: str, index: int, needle_len: int) -> tuple[int, str]:
    line = text.count("\n", 0, index) + 1
    start = max(0, index - _SNIPPET_RADIUS)
    end = min(len(text), index + needle_len + _SNIPPET_RADIUS)
    raw = " ".join(text[start:end].split())
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return line, f"{prefix}{raw}{suffix}"


def _search_results_sync(
    query: str,
    results_dir: Path,
    *,
    max_results: int = 50,
    max_file_bytes: int = _MAX_SEARCH_FILE_BYTES,
) -> list[SearchMatch]:
    needle = query.strip().lower()
    if not needle or not results_dir.is_dir():
        return []

    files = _list_results_sync(results_dir)
    matches: list[SearchMatch] = []
    for entry in files:
        if len(matches) >= max_results:
            break
        path = results_dir / entry["name"]
        try:
            with path.open("rb") as handle:
                text = handle.read(max_file_bytes).decode("utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        first_idx = lower.find(needle)
        if first_idx == -1:
            continue
        match_count = lower.count(needle)
        line, snippet = _build_snippet(text, first_idx, len(needle))
        matches.append(
            {
                "uri": entry["uri"],
                "name": entry["name"],
                "file_uri": path_to_file_uri(path),
                "size_bytes": entry["size_bytes"],
                "modified": entry["modified"],
                "source_url": entry["source_url"],
                "line": line,
                "snippet": snippet,
                "match_count": match_count,
            }
        )
    return matches


async def search_results(
    query: str,
    results_dir: Path,
    *,
    max_results: int = 50,
    max_file_bytes: int = _MAX_SEARCH_FILE_BYTES,
) -> list[SearchMatch]:
    """Full-text case-insensitive search across saved Markdown crawl results."""
    return await anyio.to_thread.run_sync(
        lambda: _search_results_sync(query, results_dir, max_results=max_results, max_file_bytes=max_file_bytes)
    )
