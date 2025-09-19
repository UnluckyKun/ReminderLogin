"""Launch the Reminder Login UI without leaving a console window open."""

from reminder_login.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main(["--from-launcher"]))
