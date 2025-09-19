"""Command line interface for the Reminder Login helper."""

from __future__ import annotations

import argparse
import sys

from . import run
from .autostart import (
    AutostartUnsupportedError,
    autostart_destination_description,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    supports_autostart,
)
from .launcher import launch_detached


def main(argv: list[str] | None = None) -> int:
    """Parse command line arguments and start the application."""

    parser = argparse.ArgumentParser(description="Daily login reminder helper")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--background",
        "-b",
        action="store_true",
        help="launch the reminder in the background and return immediately",
    )
    mode_group.add_argument(
        "--install-autostart",
        action="store_true",
        help="register the helper to start automatically when logging in",
    )
    mode_group.add_argument(
        "--remove-autostart",
        action="store_true",
        help="remove the automatic start registration",
    )
    mode_group.add_argument(
        "--autostart-status",
        action="store_true",
        help="show whether auto-start on login is currently enabled",
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

    if args.install_autostart:
        if not supports_autostart():
            parser.error("automatic start is not supported on this platform")
        try:
            entry = enable_autostart()
        except AutostartUnsupportedError as exc:
            parser.error(str(exc))
        else:
            print(f"Auto-start enabled. Configuration saved to {entry}.")
        return 0

    if args.remove_autostart:
        if not supports_autostart():
            parser.error("automatic start is not supported on this platform")
        try:
            disable_autostart()
        except AutostartUnsupportedError as exc:
            parser.error(str(exc))
        else:
            print("Auto-start disabled.")
        return 0

    if args.autostart_status:
        if not supports_autostart():
            print("Automatic start configuration is not available on this platform.")
        else:
            enabled = is_autostart_enabled()
            location = autostart_destination_description()
            if enabled:
                message = "Auto-start is currently enabled"
            else:
                message = "Auto-start is currently disabled"
            if location:
                message += f" (configuration file: {location})"
            print(message + ".")
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
