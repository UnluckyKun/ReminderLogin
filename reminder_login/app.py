"""Tkinter user interface for the Reminder Login helper."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime, time, timedelta
from tkinter import messagebox, ttk
from typing import Dict, Optional

from .storage import AppState, GameStatus, ensure_today, load_state, save_state, current_date

WINDOW_PADDING = 20
TITLE = "Daily Login Reminder"


class ReminderApp:
    """Main application controller."""

    def __init__(self) -> None:
        self.state: AppState = load_state()
        ensure_today(self.state)
        save_state(self.state)

        self.root = tk.Tk()
        self.root.title(TITLE)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        self.main_frame = ttk.Frame(self.root, padding=12)
        self.main_frame.pack(fill="both", expand=True)

        self.checkbox_vars: Dict[str, tk.BooleanVar] = {}
        self.manage_window: Optional[tk.Toplevel] = None
        self.add_window: Optional[tk.Toplevel] = None

        self.build_main_view()
        self.root.after(200, self.position_window_top_right)
        self.schedule_midnight_reset()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def build_main_view(self) -> None:
        """Construct the main window widgets."""

        for child in self.main_frame.winfo_children():
            child.destroy()

        title_label = ttk.Label(self.main_frame, text=TITLE, font=("Helvetica", 14, "bold"))
        title_label.pack(anchor="center")

        subtitle = ttk.Label(
            self.main_frame,
            text="ติ๊กว่าได้ล็อคอินเกมแล้วหรือยังวันนี้",
            font=("Helvetica", 10),
        )
        subtitle.pack(anchor="center", pady=(0, 10))

        container = ttk.Frame(self.main_frame)
        container.pack(fill="both", expand=True)

        tracked_games = list(self.state.tracked_games)
        tracked_games.sort(key=str.lower)

        self.checkbox_vars.clear()
        if tracked_games:
            for game in tracked_games:
                status = self.state.login_status.get(game)
                logged = bool(status.logged) if isinstance(status, GameStatus) else False
                var = tk.BooleanVar(value=logged)
                checkbox = ttk.Checkbutton(
                    container,
                    text=game,
                    variable=var,
                    command=lambda g=game, v=var: self.on_toggle_game(g, v),
                )
                checkbox.pack(anchor="w", pady=2)
                self.checkbox_vars[game] = var
        else:
            empty_label = ttk.Label(
                container,
                text="ยังไม่ได้เลือกเกมให้แจ้งเตือน\nกดปุ่ม 'จัดการรายชื่อเกม' เพื่อเลือก",
                justify="center",
            )
            empty_label.pack(pady=10)

        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill="x", pady=(12, 0))

        manage_btn = ttk.Button(button_frame, text="จัดการรายชื่อเกม", command=self.open_manage_games)
        manage_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        add_btn = ttk.Button(button_frame, text="เพิ่มเกมใหม่", command=self.open_add_game)
        add_btn.pack(side="left", expand=True, fill="x")

        reset_btn = ttk.Button(
            self.main_frame,
            text="เริ่มใหม่สำหรับวันนี้",
            command=self.reset_for_today,
        )
        reset_btn.pack(fill="x", pady=(10, 0))

    def position_window_top_right(self) -> None:
        """Place the window on the top-right corner of the primary display."""

        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()

        x = max(screen_width - width - WINDOW_PADDING, 0)
        y = WINDOW_PADDING
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def on_toggle_game(self, game: str, var: tk.BooleanVar) -> None:
        """Persist the checkbox state for a game."""

        logged = bool(var.get())
        today = current_date()
        self.state.login_status[game] = GameStatus(date=today, logged=logged)
        save_state(self.state)

    def open_manage_games(self) -> None:
        """Open a window to pick which games should be tracked."""

        if self.manage_window is not None and self.manage_window.winfo_exists():
            self.manage_window.focus_set()
            return

        window = tk.Toplevel(self.root)
        window.title("จัดการรายชื่อเกม")
        window.resizable(False, False)
        self.manage_window = window

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="เลือกเกมที่อยากให้แจ้งเตือน", font=("Helvetica", 11, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            frame,
            text="ติ๊กถูกเพื่อให้มีเตือนประจำวัน",
        ).pack(anchor="w", pady=(0, 8))

        all_games = sorted(set(self.state.games), key=str.lower)
        vars_map: Dict[str, tk.BooleanVar] = {}
        for game in all_games:
            var = tk.BooleanVar(value=game in self.state.tracked_games)
            ttk.Checkbutton(frame, text=game, variable=var).pack(anchor="w", pady=2)
            vars_map[game] = var

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", pady=(10, 0))

        def apply_changes() -> None:
            selected = [game for game, checkbox_var in vars_map.items() if checkbox_var.get()]
            if not selected:
                if not messagebox.askyesno(
                    "ยืนยัน",
                    "คุณยังไม่ได้เลือกเกมให้เตือนเลย\nต้องการบันทึกแบบนี้ไหม?",
                    parent=window,
                ):
                    return
            self.state.tracked_games = selected
            ensure_today(self.state)
            save_state(self.state)
            self.build_main_view()
            window.destroy()
            self.manage_window = None

        ttk.Button(button_row, text="บันทึก", command=apply_changes).pack(side="left", expand=True, fill="x")
        ttk.Button(button_row, text="ปิด", command=lambda: on_close()).pack(
            side="left", expand=True, fill="x", padx=(8, 0)
        )

        def on_close() -> None:
            self.manage_window = None
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def open_add_game(self) -> None:
        """Show a dialog to add a new game to the list."""

        if self.add_window is not None and self.add_window.winfo_exists():
            self.add_window.focus_set()
            return

        window = tk.Toplevel(self.root)
        window.title("เพิ่มเกมใหม่")
        window.resizable(False, False)
        self.add_window = window

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="ชื่อเกม", font=("Helvetica", 11, "bold")).pack(anchor="w")
        entry = ttk.Entry(frame, width=30)
        entry.pack(fill="x", pady=(4, 8))
        entry.focus_set()

        track_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="ติดตามเกมนี้เลย", variable=track_var).pack(anchor="w")

        status_label = ttk.Label(frame, foreground="red")
        status_label.pack(anchor="w", pady=(6, 0))

        def add_game() -> None:
            name = entry.get().strip()
            if not name:
                status_label.config(text="กรุณากรอกชื่อเกม")
                return
            if name in self.state.games:
                status_label.config(text="มีเกมนี้อยู่แล้ว")
                return
            self.state.games.append(name)
            if track_var.get() and name not in self.state.tracked_games:
                self.state.tracked_games.append(name)
            ensure_today(self.state)
            save_state(self.state)
            self.build_main_view()
            window.destroy()
            self.add_window = None

        ttk.Button(frame, text="เพิ่มเกม", command=add_game).pack(fill="x", pady=(10, 0))

        def on_close() -> None:
            self.add_window = None
            window.destroy()

        window.protocol("WM_DELETE_WINDOW", on_close)

    def reset_for_today(self) -> None:
        """Reset all tracked games to not logged for the current day."""

        today = current_date()
        for game in self.state.tracked_games:
            self.state.login_status[game] = GameStatus(date=today, logged=False)
        save_state(self.state)
        self.build_main_view()

    # ------------------------------------------------------------------
    # Scheduling helpers
    # ------------------------------------------------------------------
    def schedule_midnight_reset(self) -> None:
        """Schedule a reset at the next midnight."""

        now = datetime.now()
        tomorrow = now.date() + timedelta(days=1)
        midnight = datetime.combine(tomorrow, time.min)
        delay_ms = max(int((midnight - now).total_seconds() * 1000), 1000)
        self.root.after(delay_ms, self.reset_for_new_day)

    def reset_for_new_day(self) -> None:
        """Reset login status for a new day and reschedule the timer."""

        ensure_today(self.state)
        save_state(self.state)
        self.build_main_view()
        self.schedule_midnight_reset()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Start the Tkinter main loop."""

        self.root.mainloop()


def run() -> None:
    """Convenience function to run the application."""

    ReminderApp().run()
