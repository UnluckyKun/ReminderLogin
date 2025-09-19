"""Platform helpers for registering the reminder app to launch on login."""
from __future__ import annotations

import os
import plistlib
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional

APP_ROOT = Path(__file__).resolve().parent.parent
IDENTIFIER = "com.reminderlogin.helper"


class AutostartUnsupportedError(RuntimeError):
    """Raised when the current platform does not support auto-start helpers."""


def supports_autostart() -> bool:
    """Return ``True`` if automatic start on login is supported."""

    return sys.platform.startswith("linux") or sys.platform in {"win32", "darwin"}


def _entry_path() -> Path:
    if sys.platform == "win32":
        startup_dir = os.environ.get("APPDATA")
        if not startup_dir:
            raise AutostartUnsupportedError("ไม่พบโฟลเดอร์ Startup ของผู้ใช้")
        return Path(startup_dir) / "Microsoft/Windows/Start Menu/Programs/Startup" / "ReminderLoginLauncher.vbs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / f"{IDENTIFIER}.plist"
    if sys.platform.startswith("linux"):
        return Path.home() / ".config" / "autostart" / "reminder-login.desktop"
    raise AutostartUnsupportedError("ระบบปฏิบัติการนี้ยังไม่รองรับการตั้งค่าเริ่มอัตโนมัติ")


def is_autostart_enabled() -> bool:
    """Return whether the helper is registered to start on login."""

    try:
        return _entry_path().exists()
    except AutostartUnsupportedError:
        return False


def _python_command_for_gui() -> str:
    python_executable = Path(sys.executable)
    if sys.platform == "win32":
        if python_executable.name.lower() == "python.exe":
            pythonw = python_executable.with_name("pythonw.exe")
            if pythonw.exists():
                python_executable = pythonw
    return str(python_executable)


def _install_windows(entry: Path) -> None:
    entry.parent.mkdir(parents=True, exist_ok=True)
    launcher = APP_ROOT / "launch_reminder_login.pyw"
    command = f'{_python_command_for_gui()} "{launcher}"'
    escaped = command.replace('"', '""')
    script = (
        'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.Run "{escaped}", 0\n'
    )
    entry.write_text(script, encoding="utf-8")


def _install_linux(entry: Path) -> None:
    entry.parent.mkdir(parents=True, exist_ok=True)
    python_executable = shlex.quote(_python_command_for_gui())
    main_script = shlex.quote(str(APP_ROOT / "main.py"))
    working_dir = shlex.quote(str(APP_ROOT))
    command = f"cd {working_dir} && {python_executable} {main_script} --background"
    exec_line = f"sh -lc {shlex.quote(command)}"
    desktop_entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Version=1.0\n"
        "Name=Reminder Login\n"
        "Comment=แจ้งเตือนสถานะล็อกอินเกมประจำวัน\n"
        f"Exec={exec_line}\n"
        f"Path={str(APP_ROOT)}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    entry.write_text(desktop_entry, encoding="utf-8")


def _install_darwin(entry: Path) -> None:
    entry.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": IDENTIFIER,
        "ProgramArguments": [
            _python_command_for_gui(),
            str(APP_ROOT / "main.py"),
            "--background",
        ],
        "RunAtLoad": True,
        "WorkingDirectory": str(APP_ROOT),
    }
    with entry.open("wb") as fp:
        plistlib.dump(payload, fp)
    subprocess.run(["launchctl", "load", str(entry)], check=False)


def enable_autostart() -> Path:
    """Register the helper to start automatically when the user logs in."""

    entry = _entry_path()
    if sys.platform == "win32":
        _install_windows(entry)
    elif sys.platform == "darwin":
        _install_darwin(entry)
    elif sys.platform.startswith("linux"):
        _install_linux(entry)
    else:  # pragma: no cover - defensive
        raise AutostartUnsupportedError("ระบบปฏิบัติการนี้ยังไม่รองรับการตั้งค่าเริ่มอัตโนมัติ")
    return entry


def disable_autostart() -> None:
    """Remove the automatic start registration if present."""

    entry = _entry_path()
    try:
        if entry.exists():
            if sys.platform == "darwin":
                subprocess.run(["launchctl", "unload", str(entry)], check=False)
            entry.unlink()
    except FileNotFoundError:
        pass


def autostart_destination_description() -> Optional[str]:
    """Return the path used for auto-start registration, if determinable."""

    try:
        return str(_entry_path())
    except AutostartUnsupportedError:
        return None


__all__ = [
    "supports_autostart",
    "is_autostart_enabled",
    "enable_autostart",
    "disable_autostart",
    "autostart_destination_description",
    "AutostartUnsupportedError",
]

