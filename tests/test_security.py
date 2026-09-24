import os
from pathlib import Path

import pytest

from crawl4ai_mcp_llm import security
from crawl4ai_mcp_llm.crawler import crawl_and_output_to_markdown
from crawl4ai_mcp_llm.security import (
    SafeURLFilter,
    ValidationError,
    is_safe_path,
    resolve_output_path,
    validate_url,
    validate_wait_for,
)


def test_is_safe_path(tmp_path):
    base_dir = tmp_path / "results"
    base_dir.mkdir()

    for path in [base_dir / "test.md", base_dir / "subdir" / "test.md"]:
        assert is_safe_path(path, base_dir), path
    for path in [Path("/etc/passwd"), base_dir / ".." / "secret.txt", tmp_path, base_dir / "../../etc/passwd"]:
        assert not is_safe_path(path, base_dir), path


def test_is_safe_path_other_drive(tmp_path, monkeypatch):
    def commonpath_across_drives(paths):
        raise ValueError("Paths don't have the same drive")

    monkeypatch.setattr(os.path, "commonpath", commonpath_across_drives)

    assert not is_safe_path(Path("D:/etc/passwd"), tmp_path)
    with pytest.raises(ValidationError):
        resolve_output_path("D:/etc/passwd.md", tmp_path)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks not supported")
def test_is_safe_path_rejects_symlink_escape(tmp_path):
    base_dir = tmp_path / "results"
    base_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (base_dir / "evil").symlink_to(outside)

    assert not is_safe_path(base_dir / "evil" / "shadow", base_dir)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/docs", "https://example.com/docs"),
        ("http://example.com", "http://example.com"),
        ("example.com/path", "https://example.com/path"),
    ],
)
async def test_validate_url_accepts_public_http(url, expected):
    assert await validate_url(url) == expected


@pytest.mark.anyio
@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "raw:<html><body>x</body></html>",
        "raw://<html></html>",
        "data:text/html,hello",
        "javascript:alert(1)",
        "ftp://example.com/file",
        "https://",
        "",
        "http://localhost:8080",
        "localhost:8080",
        "http://127.0.0.1/",
        "http://10.0.0.5/admin",
        "http://192.168.1.1",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:3000/",
        "http://[::ffff:127.0.0.1]/",
        "http://0.0.0.0:8000",
    ],
)
async def test_validate_url_rejects_unsafe_targets(url):
    with pytest.raises(ValidationError):
        await validate_url(url)


@pytest.mark.anyio
async def test_validate_url_rejects_hosts_resolving_to_private_ips(monkeypatch):
    async def resolve_to_private(hostname):
        return ["10.1.2.3"]

    monkeypatch.setattr(security, "resolve_host", resolve_to_private)

    with pytest.raises(ValidationError, match="non-public"):
        await validate_url("https://intranet.example.com")


@pytest.mark.anyio
async def test_validate_url_allows_private_networks_when_enabled():
    assert await validate_url("http://127.0.0.1:8000", allow_private_networks=True) == "http://127.0.0.1:8000"
    with pytest.raises(ValidationError):
        await validate_url("file:///etc/passwd", allow_private_networks=True)


@pytest.mark.anyio
async def test_crawl_rejects_file_urls_before_launching_browser(fake_crawler):
    result = await crawl_and_output_to_markdown("file:///etc/passwd")

    assert "Unsupported URL scheme" in result["error"]
    assert fake_crawler.calls == []


def test_safe_url_filter():
    link_filter = SafeURLFilter()
    assert link_filter.apply("https://example.com/page")
    for url in ["file:///etc/passwd", "javascript:alert(1)", "http://127.0.0.1/", "http://localhost/", "mailto:a@b.c"]:
        assert not link_filter.apply(url), url
    assert SafeURLFilter(allow_private_networks=True).apply("http://127.0.0.1/")


@pytest.mark.parametrize(
    ("wait_for", "expected"),
    [(None, None), ("  ", None), ("#app", "css:#app"), ("css:.ready", "css:.ready"), ("div > p", "css:div > p")],
)
def test_validate_wait_for_without_js(wait_for, expected):
    assert validate_wait_for(wait_for, allow_js=False) == expected


def test_resolve_output_path(tmp_path):
    base_dir = tmp_path / "results"
    base_dir.mkdir()

    assert resolve_output_path("report", base_dir) == base_dir / "report.md"
    assert resolve_output_path("sub/re:port?.md", base_dir) == base_dir / "sub" / "re_port_.md"
    assert resolve_output_path(str(base_dir / "abs.md"), base_dir) == base_dir / "abs.md"
    for unsafe in ["../escape.md", "/etc/passwd", "sub/../../escape.md"]:
        with pytest.raises(ValidationError):
            resolve_output_path(unsafe, base_dir)


def test_resolve_output_path_refuses_overwrite(tmp_path):
    (tmp_path / "existing.md").write_text("keep me")

    with pytest.raises(ValidationError, match="already exists"):
        resolve_output_path("existing.md", tmp_path)
    assert resolve_output_path("existing.md", tmp_path, overwrite=True) == tmp_path / "existing.md"
