"""Utilities for launching the Reminder Login app in different modes."""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Iterable, List, Sequence


def _build_base_args(extra: Sequence[str] | None = None) -> List[str]:
    """Return the command used to spawn the UI process."""

    args: List[str] = [sys.executable, "-m", "reminder_login", "--from-launcher"]
    if extra:
        args.extend(extra)
    return args


def launch_detached(*, extra_args: Iterable[str] | None = None) -> subprocess.Popen[bytes]:
    """Start the UI in a new process that is detached from the current terminal.

    Parameters
    ----------
    extra_args:
        Optional additional command line arguments that should be forwarded to
        the spawned process.

    Returns
    -------
    subprocess.Popen
        Handle to the spawned process. The caller is not expected to interact
        with it, but the handle can be used for troubleshooting if necessary.
    """

    args = _build_base_args(list(extra_args) if extra_args else None)

    popen_kwargs = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )

    if sys.platform == "win32":
        creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(args, creationflags=creationflags, **popen_kwargs)

    # POSIX platforms
    if hasattr(subprocess, "START_NEW_SESSION"):
        popen_kwargs["start_new_session"] = True  # type: ignore[assignment]
    else:
        popen_kwargs["preexec_fn"] = os.setsid  # type: ignore[assignment]

    return subprocess.Popen(args, **popen_kwargs)


__all__ = ["launch_detached"]

