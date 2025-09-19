"""Reminder Login desktop helper."""

from .app import ReminderApp, run
from .autostart import (
    autostart_destination_description,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    supports_autostart,
)
from .launcher import launch_detached

__all__ = [
    "ReminderApp",
    "run",
    "launch_detached",
    "supports_autostart",
    "is_autostart_enabled",
    "enable_autostart",
    "disable_autostart",
    "autostart_destination_description",
]
