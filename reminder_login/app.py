"""Tkinter user interface for the Reminder Login helper."""
from __future__ import annotations

import csv
import subprocess
import sys
import tkinter as tk
from datetime import datetime, time, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, Optional, Set

from .autostart import (
    AutostartUnsupportedError,
    autostart_destination_description,
    disable_autostart,
    enable_autostart,
    is_autostart_enabled,
    supports_autostart,
)
from .storage import AppState, GameStatus, ensure_today, load_state, save_state, current_date

WINDOW_PADDING = 20
TITLE = "Daily Login Reminder"
PROCESS_POLL_INTERVAL_MS = 5000


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
        self.autostart_supported = supports_autostart()
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())

        self.build_main_view()
        self.root.after(200, self.position_window_top_right)
        self.schedule_midnight_reset()
        self.root.after(PROCESS_POLL_INTERVAL_MS, self.poll_game_processes)

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

        autostart_frame = ttk.Frame(self.main_frame)
        autostart_frame.pack(fill="x", pady=(8, 0))
        if self.autostart_supported:
            ttk.Checkbutton(
                autostart_frame,
                text="เปิดเองอัตโนมัติเมื่อเข้าสู่ระบบ",
                variable=self.autostart_var,
                command=self.on_toggle_autostart,
            ).pack(anchor="w")
        else:
            ttk.Label(
                autostart_frame,
                text="ฟีเจอร์เริ่มอัตโนมัติยังไม่รองรับบนระบบนี้",
                foreground="grey",
            ).pack(anchor="w")

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
        path_map: Dict[str, Optional[str]] = {
            game: self.state.game_paths.get(game) for game in all_games
        }
        path_labels: Dict[str, ttk.Label] = {}

        list_container = ttk.Frame(frame)
        list_container.pack(fill="both", expand=True)

        for row, game in enumerate(all_games):
            item_frame = ttk.Frame(list_container)
            item_frame.grid(row=row, column=0, sticky="ew", pady=3)
            item_frame.columnconfigure(0, weight=1)
            item_frame.columnconfigure(1, weight=0)
            item_frame.columnconfigure(2, weight=0)

            var = tk.BooleanVar(value=game in self.state.tracked_games)
            vars_map[game] = var

            ttk.Checkbutton(item_frame, text=game, variable=var).grid(
                row=0, column=0, sticky="w"
            )

            def select_file(target: str = game) -> None:
                filename = filedialog.askopenfilename(
                    parent=window,
                    title=f"เลือกไฟล์สำหรับ {target}",
                )
                if filename:
                    path_map[target] = filename
                    path_labels[target].config(
                        text=self.format_path_label(filename),
                        foreground="#1a1a1a",
                    )

            def clear_file(target: str = game) -> None:
                path_map[target] = None
                path_labels[target].config(
                    text=self.format_path_label(None),
                    foreground="grey",
                )

            ttk.Button(item_frame, text="เลือกไฟล์…", command=select_file).grid(
                row=0, column=1, padx=(6, 0), sticky="e"
            )
            ttk.Button(item_frame, text="ล้าง", command=clear_file).grid(
                row=0, column=2, padx=(4, 0), sticky="e"
            )

            label = ttk.Label(
                item_frame,
                text=self.format_path_label(path_map[game]),
                foreground="grey" if not path_map[game] else "#1a1a1a",
                wraplength=360,
                justify="left",
            )
            label.grid(row=1, column=0, columnspan=3, sticky="w", padx=(24, 0), pady=(2, 0))
            path_labels[game] = label

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
            self.state.game_paths = {
                game: path
                for game, path in path_map.items()
                if path and game in self.state.games
            }
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

        path_var = tk.StringVar()
        ttk.Label(frame, text="ไฟล์เกม (ไม่บังคับ)").pack(anchor="w", pady=(10, 2))
        path_row = ttk.Frame(frame)
        path_row.pack(fill="x")
        path_entry = ttk.Entry(path_row, textvariable=path_var)
        path_entry.pack(side="left", expand=True, fill="x")

        def browse_file() -> None:
            filename = filedialog.askopenfilename(parent=window, title="เลือกไฟล์เกม")
            if filename:
                path_var.set(filename)

        ttk.Button(path_row, text="เลือกไฟล์…", command=browse_file).pack(
            side="left", padx=(6, 0)
        )

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
            selected_path = path_var.get().strip()
            if selected_path:
                path_obj = Path(selected_path)
                if not path_obj.exists():
                    status_label.config(text="หาไฟล์นี้ไม่พบ ลองเลือกใหม่อีกครั้ง")
                    return
                self.state.game_paths[name] = str(path_obj)
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

    def on_toggle_autostart(self) -> None:
        """Enable or disable launching on login based on the checkbox state."""

        desired = bool(self.autostart_var.get())
        if not self.autostart_supported:
            messagebox.showerror(
                "ไม่รองรับ",
                "ระบบปฏิบัติการนี้ยังไม่รองรับการตั้งค่าให้เปิดอัตโนมัติ",
                parent=self.root,
            )
            self.autostart_var.set(False)
            return

        try:
            if desired:
                entry = enable_autostart()
                location = autostart_destination_description()
                message = "ตั้งค่าให้เปิดอัตโนมัติเรียบร้อยแล้ว"
                if location:
                    message += f"\nไฟล์กำหนดอยู่ที่:\n{location}"
                messagebox.showinfo("สำเร็จ", message, parent=self.root)
            else:
                disable_autostart()
                messagebox.showinfo(
                    "สำเร็จ",
                    "ปิดการเริ่มอัตโนมัติแล้ว",
                    parent=self.root,
                )
        except AutostartUnsupportedError as exc:
            messagebox.showerror("ไม่รองรับ", str(exc), parent=self.root)
            self.autostart_var.set(False)
        except OSError as exc:
            messagebox.showerror("ผิดพลาด", str(exc), parent=self.root)
            self.autostart_var.set(is_autostart_enabled())
        else:
            self.autostart_var.set(is_autostart_enabled())

    def poll_game_processes(self) -> None:
        """Check running processes and tick games that are currently open."""

        try:
            tracked = [
                (game, self.state.game_paths.get(game))
                for game in self.state.tracked_games
            ]
        except Exception:  # pragma: no cover - defensive
            tracked = []

        tracked = [(game, path) for game, path in tracked if path]
        if tracked:
            running = self.list_running_process_names()
            if running:
                today = current_date()
                changed = False
                for game, path in tracked:
                    candidates = self.possible_process_names(path)
                    if any(candidate in running for candidate in candidates):
                        status = self.state.login_status.get(game)
                        if status is None or status.date != today or not status.logged:
                            self.state.login_status[game] = GameStatus(
                                date=today, logged=True
                            )
                            checkbox_var = self.checkbox_vars.get(game)
                            if checkbox_var is not None:
                                checkbox_var.set(True)
                            changed = True
                if changed:
                    save_state(self.state)

        self.root.after(PROCESS_POLL_INTERVAL_MS, self.poll_game_processes)

    @staticmethod
    def list_running_process_names() -> Set[str]:
        """Return a set with the lowercase names of currently running processes."""

        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["tasklist", "/fo", "csv", "/nh"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except OSError:
                return set()
            reader = csv.reader(result.stdout.splitlines())
            return {row[0].strip().lower() for row in reader if row}

        try:
            result = subprocess.run(
                ["ps", "-A", "-o", "comm="],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            return set()
        names: Set[str] = set()
        for line in result.stdout.splitlines():
            name = line.strip()
            if not name:
                continue
            names.add(Path(name).name.lower())
        return names

    @staticmethod
    def possible_process_names(path: str) -> Set[str]:
        """Derive candidate process names for a given executable path."""

        candidate = Path(path)
        names = {candidate.name.lower()}
        stem = candidate.stem.lower()
        if stem:
            names.add(stem)
        if candidate.suffix.lower() == ".app":
            names.add(candidate.stem.lower())
        return {name for name in names if name}

    @staticmethod
    def format_path_label(path: Optional[str]) -> str:
        """Return a friendly label for the selected executable path."""

        if not path:
            return "ยังไม่ได้ตั้งค่าไฟล์สำหรับตรวจจับอัตโนมัติ"
        display = str(Path(path))
        if len(display) > 70:
            display = f"…{display[-67:]}"
        return f"ไฟล์ที่ใช้ตรวจจับ: {display}"

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Start the Tkinter main loop."""

        self.root.mainloop()


def run() -> None:
    """Convenience function to run the application."""

    ReminderApp().run()
