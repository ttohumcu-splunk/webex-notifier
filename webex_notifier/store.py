"""Load/save JSON config files with 0600 permissions (they hold tokens/secrets)."""
import json
import os
from pathlib import Path
from typing import Any, Optional

from .paths import APP_CONFIG_FILE, STATE_FILE, ensure_config_dir


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r") as f:
        return json.load(f)


def _write(path: Path, data: dict) -> None:
    ensure_config_dir()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def load_app_config() -> dict:
    """Org-wide OAuth app credentials (Webex Integration + Slack App client id/secret).

    Distributed out-of-band by whoever registered the apps -- never committed to git.
    """
    return _read(APP_CONFIG_FILE)


def save_app_config(data: dict) -> None:
    _write(APP_CONFIG_FILE, data)


def load_state() -> dict:
    """Per-user tokens, identity, and lastCheck watermark."""
    return _read(STATE_FILE)


def save_state(data: dict) -> None:
    _write(STATE_FILE, data)


def update_state(**kwargs: Any) -> dict:
    state = load_state()
    state.update(kwargs)
    save_state(state)
    return state
