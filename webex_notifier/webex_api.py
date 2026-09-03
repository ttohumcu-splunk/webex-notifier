"""Thin wrapper over the Webex REST API used by the poller.

Deliberately mirrors the approach worked out by hand during initial testing:
webex_search() errors with "Too many rooms" once an account has hundreds of
spaces, so mentions/DMs are found by listing rooms, filtering client-side to
those with recent lastActivity, and only then paging messages in *those* rooms.
"""
import time
from datetime import datetime, timezone
from typing import Iterable, Optional

import requests

from .webex_auth import get_valid_access_token

BASE_URL = "https://webexapis.com/v1"


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _request(method: str, path: str, **kwargs) -> dict:
    token = get_valid_access_token()
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    for attempt in range(3):
        resp = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
        if resp.status_code == 429:
            time.sleep(int(resp.headers.get("Retry-After", 5)))
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}


def list_rooms(room_type: str, since: Optional[datetime] = None) -> list[dict]:
    """room_type: 'direct' or 'group'. Filters client-side to rooms active after `since`."""
    data = _request("GET", "/rooms", params={"type": room_type, "max": 500})
    rooms = data.get("items", [])
    if since is None:
        return rooms
    return [r for r in rooms if "lastActivity" in r and _parse_iso(r["lastActivity"]) > since]


def list_new_messages(room_id: str, since: datetime, max_pages: int = 5, page_size: int = 50) -> list[dict]:
    """Messages created after `since` in a room, newest first. Pages backwards via beforeMessage."""
    collected: list[dict] = []
    before_message = None
    for _ in range(max_pages):
        params = {"roomId": room_id, "max": page_size}
        if before_message:
            params["beforeMessage"] = before_message
        data = _request("GET", "/messages", params=params)
        items = data.get("items", [])
        if not items:
            break
        hit_boundary = False
        for m in items:
            if _parse_iso(m["created"]) <= since:
                hit_boundary = True
                break
            collected.append(m)
        if hit_boundary or len(items) < page_size:
            break
        before_message = items[-1]["id"]
    return collected


def get_me() -> dict:
    return _request("GET", "/people/me")


def check_connection() -> dict:
    """Returns {'ok': True, 'displayName': ...} or {'ok': False, 'error': ...} -- never raises."""
    try:
        me = get_me()
        return {"ok": True, "displayName": me.get("displayName")}
    except Exception as exc:  # noqa: BLE001 -- doctor needs a message, not a traceback
        return {"ok": False, "error": str(exc)}
