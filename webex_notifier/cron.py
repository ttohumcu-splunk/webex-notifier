"""Install/remove a personal crontab entry so the check runs unattended, with no
Claude Code session (or anything else) needing to stay open.
"""
import shutil
import subprocess
import sys

from .paths import CRON_MARKER, LOG_FILE, ensure_config_dir

SCHEDULE = "* * * * *"


def _require_crontab() -> None:
    if shutil.which("crontab") is None:
        raise SystemExit(
            "No 'crontab' command found on this machine, so the periodic check can't be "
            "scheduled automatically. Install cron (e.g. via your OS package manager) or "
            "run 'webex-notifier check' periodically some other way."
        )


def _current_crontab() -> str:
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def _cron_line() -> str:
    python = sys.executable
    return f"{SCHEDULE} {python} -m webex_notifier check >> {LOG_FILE} 2>&1 {CRON_MARKER}"


def install() -> None:
    _require_crontab()
    ensure_config_dir()
    existing = _current_crontab()
    lines = [l for l in existing.splitlines() if CRON_MARKER not in l]
    lines.append(_cron_line())
    new_crontab = "\n".join(lines) + "\n"
    result = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"Failed to install cron job: {result.stderr.strip()}")
    print(f"Installed cron job: runs every minute, logs to {LOG_FILE}")


def uninstall() -> None:
    _require_crontab()
    existing = _current_crontab()
    lines = [l for l in existing.splitlines() if CRON_MARKER not in l]
    new_crontab = "\n".join(lines) + ("\n" if lines else "")
    result = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"Failed to remove cron job: {result.stderr.strip()}")
    print("Removed webex-notifier cron job.")


def is_installed() -> bool:
    return CRON_MARKER in _current_crontab()
