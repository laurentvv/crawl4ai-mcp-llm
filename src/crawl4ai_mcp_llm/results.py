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


class ResultFile(TypedDict):
    uri: str
    name: str
    size_bytes: int
    modified: str
    source_url: str | None


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


async def _source_url(path: anyio.Path) -> str | None:
    async with await path.open("rb") as handle:
        header = (await handle.read(_HEADER_BYTES)).decode("utf-8", errors="ignore")
    match = _SOURCE_URL_REGEX.search(header)
    return match.group(1) if match else None


async def list_results(results_dir: Path) -> list[ResultFile]:
    """List saved results (newest first) with the URL of their first page."""
    root = anyio.Path(results_dir)
    if not await root.is_dir():
        return []
    entries: list[tuple[float, ResultFile]] = []
    async for path in root.rglob("*.md"):
        if not await path.is_file() or not is_safe_path(Path(path), results_dir):
            continue
        stat = await path.stat()
        relative = Path(path).relative_to(results_dir).as_posix()
        entries.append(
            (
                stat.st_mtime,
                {
                    "uri": RESULT_URI_PREFIX + relative,
                    "name": relative,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                    "source_url": await _source_url(path),
                },
            )
        )
    entries.sort(key=lambda entry: entry[0], reverse=True)
    return [entry for _, entry in entries]
