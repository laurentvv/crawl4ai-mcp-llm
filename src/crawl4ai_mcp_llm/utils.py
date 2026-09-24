import re
import sys
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path

from .security import sanitize_filename

UNICODE_REPLACEMENTS = {
    "→": "->",  # Right arrow → becomes ->
    "←": "<-",  # Left arrow ← becomes <-
    "↑": "^",  # Up arrow ↑ becomes ^
    "↓": "v",  # Down arrow ↓ becomes v
    "•": "*",  # Bullet • becomes *
    "–": "-",  # En dash – becomes -
    "—": "--",  # Em dash — becomes --
    "‘": "'",  # Left single quotation mark ' becomes '
    "’": "'",  # Right single quotation mark ' becomes '
    "“": '"',  # Left double quotation mark " becomes "
    "”": '"',  # Right double quotation mark " becomes "
    "…": "...",  # Ellipsis … becomes ...
    " ": " ",  # Non-breaking space   becomes normal space
}


def sanitize_for_display(text: object) -> str:
    """
    Sanitize text for safe display in MCP responses (e.g. error messages).
    Replaces known problematic Unicode characters with their ASCII equivalents
    and strips remaining non-ASCII bytes.

    NOTE: Do NOT use this on crawled page content — it intentionally destroys
    typographic Unicode (quotes, dashes, bullets) to keep MCP output safe.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    if text.isascii():
        return text

    try:
        # Test if the text can be encoded in the default system encoding
        text.encode(sys.getdefaultencoding())
    except UnicodeEncodeError:
        # If it can't, replace problematic characters
        for char, replacement in UNICODE_REPLACEMENTS.items():
            if char in text:
                text = text.replace(char, replacement)

        # Eliminate all other non-ASCII characters that might cause problems
        if not text.isascii():
            text = re.sub(r"[^\x00-\x7F]+", " ", text)

    return text


def generate_filename_from_url(url: str) -> str:
    """Generate a unique, cross-platform file name from a URL."""
    parsed_url = urllib.parse.urlsplit(url)
    if not parsed_url.netloc and "://" not in url:
        # Bare domains such as "example.com" are parsed as a path.
        parsed_url = urllib.parse.urlsplit(f"//{url}")
    host = parsed_url.hostname or "page"
    if parsed_url.port:
        host = f"{host}_{parsed_url.port}"
    hostname = sanitize_filename(host.replace(".", "_"))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"crawl_{hostname}_{timestamp}_{suffix}.md"


def ensure_directory(path: Path) -> Path:
    """Create ``path`` (and parents) if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
