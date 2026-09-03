"""Filesystem locations for config/state, shared by every module."""
from pathlib import Path

CONFIG_DIR = Path.home() / ".webex_notifier"
APP_CONFIG_FILE = CONFIG_DIR / "app_config.json"
STATE_FILE = CONFIG_DIR / "state.json"
LOG_FILE = CONFIG_DIR / "monitor.log"

CRON_MARKER = "# webex-notifier"


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
