"""Input validation for crawl requests: URLs, output paths and wait conditions."""

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

import anyio
from crawl4ai.deep_crawling.filters import URLFilter

ALLOWED_SCHEMES = ("http", "https")
# Anything that crawl4ai would evaluate as JavaScript in `wait_for`.
_JS_WAIT_FOR_REGEX = re.compile(r"^\s*(?:js:|\(|function\b|async\b)|=>", re.IGNORECASE)
_UNSAFE_FILENAME_CHARS = re.compile(r"[^\w.-]+")


class ValidationError(ValueError):
    """Raised when a crawl parameter is rejected before any network access."""


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _parse_http_url(url: str) -> tuple[str, str]:
    """Return (normalised_url, hostname) or raise ValidationError."""
    url = url.strip()
    if not url:
        raise ValidationError("URL must not be empty")
    if "://" not in url and not url.lower().startswith(("raw:", "data:", "javascript:", "file:")):
        # Be lenient with bare domains such as "example.com".
        url = f"https://{url}"
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValidationError(f"Unsupported URL scheme {parts.scheme!r}: only http and https URLs can be crawled")
    if not parts.hostname:
        raise ValidationError(f"URL has no host: {url!r}")
    return url, parts.hostname


async def resolve_host(hostname: str) -> list[str]:
    """Resolve a hostname to IP addresses (patched in tests)."""
    infos = await anyio.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


async def validate_url(url: str, *, allow_private_networks: bool = False) -> str:
    """Validate a start URL and return its normalised form.

    Only http(s) URLs are accepted (crawl4ai would otherwise read ``file://``
    paths or render ``raw:`` HTML). Unless explicitly allowed, hosts that
    resolve to loopback, private, link-local or otherwise non-global addresses
    are rejected to limit SSRF towards the local network.
    """
    url, hostname = _parse_http_url(url)
    if allow_private_networks:
        return url

    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        if hostname.lower() == "localhost" or hostname.lower().endswith(".localhost"):
            raise ValidationError(f"Access to local host {hostname!r} is not allowed") from None
        try:
            resolved = await resolve_host(hostname)
        except OSError:
            # Unresolvable here means the browser cannot reach it either; let
            # the crawl report the network error.
            return url
        addresses = [ipaddress.ip_address(addr.split("%", 1)[0]) for addr in resolved]

    for address in addresses:
        if not _is_public_ip(address):
            raise ValidationError(
                f"Access to non-public address {address} ({hostname}) is not allowed. "
                "Set CRAWL4AI_MCP_ALLOW_PRIVATE_NETWORKS=true to crawl local or private networks."
            )
    return url


class SafeURLFilter(URLFilter):
    """Deep-crawl filter that drops non-http(s) links and literal private IPs.

    It runs synchronously on every discovered link, so it does not resolve DNS;
    the start URL is fully checked by :func:`validate_url`.
    """

    __slots__ = ("allow_private_networks",)

    def __init__(self, allow_private_networks: bool = False):
        super().__init__(name="SafeURLFilter")
        self.allow_private_networks = allow_private_networks

    def apply(self, url: str) -> bool:
        passed = self._check(url)
        self._update_stats(passed)
        return passed

    def _check(self, url: str) -> bool:
        parts = urlsplit(url)
        if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.hostname:
            return False
        if self.allow_private_networks:
            return True
        hostname = parts.hostname.lower()
        if hostname == "localhost" or hostname.endswith(".localhost"):
            return False
        try:
            return _is_public_ip(ipaddress.ip_address(hostname))
        except ValueError:
            return True


def validate_wait_for(wait_for: str | None, *, allow_js: bool) -> str | None:
    """Return a wait condition that cannot run JavaScript unless allowed.

    crawl4ai evaluates ``js:`` conditions, function-looking strings and even
    invalid CSS selectors as JavaScript, so without the JS opt-in the value is
    pinned to an explicit ``css:`` selector.
    """
    if not wait_for or not wait_for.strip():
        return None
    wait_for = wait_for.strip()
    if allow_js:
        return wait_for
    if wait_for.lower().startswith("css:"):
        return wait_for
    if _JS_WAIT_FOR_REGEX.search(wait_for):
        raise ValidationError(
            "JavaScript wait conditions are disabled for security reasons. Use a CSS selector, "
            "or set CRAWL4AI_MCP_ALLOW_JS=true to enable JavaScript."
        )
    return f"css:{wait_for}"


def is_safe_path(path: str | os.PathLike[str], base_dir: str | os.PathLike[str]) -> bool:
    """Check that ``path`` stays inside ``base_dir`` once symlinks and ``..`` are resolved."""
    abs_path = os.path.realpath(path)
    abs_base = os.path.realpath(base_dir)
    try:
        return os.path.commonpath([abs_path, abs_base]) == abs_base
    except ValueError:
        # Windows: paths on different drives have no common path.
        return False


def sanitize_filename(name: str) -> str:
    """Replace characters that are unsafe in file names on common platforms."""
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", name).strip("._")
    return cleaned or "crawl"


def resolve_output_path(output_file: str, results_dir: Path, *, overwrite: bool = False) -> Path:
    """Map a user supplied output file to a safe ``.md`` path inside ``results_dir``."""
    candidate = Path(output_file)
    if not candidate.is_absolute():
        candidate = results_dir / candidate
    candidate = candidate.with_name(sanitize_filename(candidate.name))
    if candidate.suffix.lower() != ".md":
        candidate = candidate.with_name(candidate.name + ".md")

    if not is_safe_path(candidate, results_dir):
        raise ValidationError(f"Invalid output path: {output_file}. Paths must be within {results_dir}")
    if candidate.exists() and not overwrite:
        raise ValidationError(f"Output file already exists: {candidate}. Pass overwrite=true or choose another name.")
    return candidate
