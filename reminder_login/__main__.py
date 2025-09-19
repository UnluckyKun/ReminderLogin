"""Command line interface for the Reminder Login helper."""

from __future__ import annotations

import argparse
import sys

from . import run
from .launcher import launch_detached


def main(argv: list[str] | None = None) -> int:
    """Parse command line arguments and start the application."""

    parser = argparse.ArgumentParser(description="Daily login reminder helper")
    parser.add_argument(
        "--background",
        "-b",
        action="store_true",
        help="launch the reminder in the background and return immediately",
    )
    parser.add_argument(
        "--from-launcher",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    args = parser.parse_args(argv)

    if args.from_launcher:
        run()
        return 0

    if args.background:
        try:
            process = launch_detached()
        except OSError as exc:  # pragma: no cover - handled at runtime
            parser.error(str(exc))
        else:
            print(f"Launched Reminder Login in the background (PID {process.pid}).")
        return 0

    run()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    sys.exit(main())
