import logging
import os
import sys

import anyio
import click

from .config import get_settings


def _configure_logging(level: str) -> None:
    # stdout carries the MCP stdio protocol: logs must go to stderr.
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@click.command()
def main() -> None:
    """Run the crawl4ai MCP server over stdio."""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _configure_logging(get_settings().log_level)

    from .server import app

    try:
        anyio.run(app.run_stdio_async)
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.getLogger(__name__).exception("MCP server stopped with an error")
        sys.exit(1)


if __name__ == "__main__":
    main()
