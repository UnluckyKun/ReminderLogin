"""State management utilities for the Reminder Login application."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List

APP_DIR = Path.home() / ".reminder_login"
STATE_FILE = APP_DIR / "state.json"

DEFAULT_GAMES = [
    "Genshin Impact",
    "Honkai: Star Rail",
    "Blue Archive",
    "Arknights",
    "Final Fantasy XIV",
]
DEFAULT_TRACKED = DEFAULT_GAMES[:3]


@dataclass
class GameStatus:
    """Represents the login status for a single game."""

    date: str
    logged: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {"date": self.date, "logged": self.logged}

    @classmethod
    def from_dict(cls, data: Dict[str, object], *, fallback_date: str) -> "GameStatus":
        if not isinstance(data, dict):
            return cls(date=fallback_date, logged=False)
        date_value = str(data.get("date", fallback_date))
        logged = bool(data.get("logged", False))
        return cls(date=date_value, logged=logged)


@dataclass
class AppState:
    """Container for the persisted application state."""

    games: List[str] = field(default_factory=list)
    tracked_games: List[str] = field(default_factory=list)
    login_status: Dict[str, GameStatus] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "games": list(self.games),
            "tracked_games": list(self.tracked_games),
            "login_status": {
                game: status.to_dict() for game, status in self.login_status.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "AppState":
        games = [str(item) for item in data.get("games", []) if isinstance(item, str)]
        tracked_games = [
            str(item)
            for item in data.get("tracked_games", [])
            if isinstance(item, str)
        ]
        raw_status = data.get("login_status", {})
        today = current_date()
        login_status: Dict[str, GameStatus] = {}
        if isinstance(raw_status, dict):
            for game, status in raw_status.items():
                login_status[str(game)] = GameStatus.from_dict(status, fallback_date=today)

        return cls(games=games, tracked_games=tracked_games, login_status=login_status)


def current_date() -> str:
    """Return today's date in ISO format."""

    return date.today().isoformat()


def ensure_app_dir() -> None:
    """Make sure the application directory exists."""

    APP_DIR.mkdir(parents=True, exist_ok=True)


def default_state() -> AppState:
    """Create a default state instance."""

    return AppState(
        games=list(DEFAULT_GAMES),
        tracked_games=list(DEFAULT_TRACKED),
        login_status={},
    )


def load_state() -> AppState:
    """Load the application state from disk."""

    ensure_app_dir()
    if not STATE_FILE.exists():
        return default_state()

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_state()

    if not isinstance(data, dict):
        return default_state()

    state = AppState.from_dict(data)
    if not state.games:
        state.games = list(DEFAULT_GAMES)
    if not state.tracked_games:
        state.tracked_games = list(DEFAULT_TRACKED)
    return state


def save_state(state: AppState) -> None:
    """Persist the application state to disk."""

    ensure_app_dir()
    serialisable = state.to_dict()
    STATE_FILE.write_text(json.dumps(serialisable, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_today(state: AppState) -> None:
    """Ensure that login status entries are initialised for the current day."""

    today = current_date()
    for game in state.tracked_games:
        status = state.login_status.get(game)
        if status is None or status.date != today:
            state.login_status[game] = GameStatus(date=today, logged=False)
    for game in list(state.login_status.keys()):
        if game not in state.tracked_games:
            state.login_status.pop(game, None)
