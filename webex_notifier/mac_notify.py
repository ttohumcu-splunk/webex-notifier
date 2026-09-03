"""Native macOS Notification Center banners -- no external service, no admin
approval, no network dependency. Useful on its own, and as a channel that
works even before/without a Slack app being approved.

The first time this fires, macOS may need you to allow notifications for
"Script Editor" (the process osascript runs as) under System Settings ->
Notifications -- if you don't see a banner the first time, check there.
"""
import subprocess
import sys


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def notify(title: str, message: str, sound: str = "Ping") -> bool:
    """Best-effort: returns True if it attempted to fire. Never raises, no-ops off macOS."""
    if sys.platform != "darwin":
        return False
    script = f'display notification "{_escape(message)}" with title "{_escape(title)}" sound name "{_escape(sound)}"'
    try:
        subprocess.run(["osascript", "-e", script], timeout=10, capture_output=True)
        return True
    except Exception:  # noqa: BLE001 -- a missed alert channel shouldn't crash the whole check
        return False
