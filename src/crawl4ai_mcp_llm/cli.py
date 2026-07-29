import sys
import traceback
import click
import anyio

from .server import app

@click.command()
def main() -> int:
    anyio.run(app.run_stdio_async)
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Main error: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)
