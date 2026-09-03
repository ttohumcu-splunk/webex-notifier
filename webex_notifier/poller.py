"""One polling pass: find new Webex DMs and @mentions since lastCheck, alert Slack.

Mirrors the hand-run logic from initial testing:
- DMs: any message in a 1:1 room not authored by me.
- Mentions: any message in a group room whose mentionedPeople includes my
  person id (Webex tags real @mentions this way), restricted to rooms whose
  lastActivity is after lastCheck so we don't rescan all ~300+ spaces.
- Bot senders (`*@webex.bot`) are excluded from both -- automated broadcasts,
  not something a human needs paged for.
"""
from datetime import datetime, timezone

from . import mac_notify, slack_api, webex_api
from .store import load_state, update_state

MAX_ITEMS_IN_SUMMARY = 15


def _is_bot(message: dict) -> bool:
    return (message.get("personEmail") or "").endswith("@webex.bot")


def _snippet(message: dict, length: int = 150) -> str:
    text = (message.get("text") or "").strip().replace("\n", " ")
    return text[:length] + ("..." if len(text) > length else "")


def _room_title(room_lookup: dict, room_id: str) -> str:
    return room_lookup.get(room_id, {}).get("title", "Unknown space")


def check_once(post_if_empty: bool = False) -> str | None:
    state = load_state()
    my_person_id = state.get("webexPersonId")
    last_check_raw = state.get("lastCheck")
    if not my_person_id or not last_check_raw:
        raise SystemExit("Not set up yet. Run: webex-notifier setup")

    since = datetime.fromisoformat(last_check_raw.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)

    findings: list[tuple[str, dict, dict]] = []  # (kind, room, message)

    direct_rooms = webex_api.list_rooms("direct", since=since)
    for room in direct_rooms:
        for message in webex_api.list_new_messages(room["id"], since):
            if message.get("personId") == my_person_id or _is_bot(message):
                continue
            findings.append(("DM", room, message))

    group_rooms = webex_api.list_rooms("group", since=since)
    for room in group_rooms:
        for message in webex_api.list_new_messages(room["id"], since):
            if message.get("personId") == my_person_id or _is_bot(message):
                continue
            if my_person_id in (message.get("mentionedPeople") or []):
                findings.append(("Mention", room, message))

    new_last_check = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    if not findings:
        update_state(lastCheck=new_last_check)
        return None

    findings.sort(key=lambda f: f[2]["created"])
    room_lookup = {r["id"]: r for r in direct_rooms + group_rooms}

    lines = [f"*Webex alert* — {len(findings)} new item(s) since last check:"]
    for kind, room, message in findings[:MAX_ITEMS_IN_SUMMARY]:
        sender = message.get("personEmail", "unknown")
        title = _room_title(room_lookup, room["id"])
        lines.append(f"• [{kind}] *{title}* — {sender}: {_snippet(message)}")
    if len(findings) > MAX_ITEMS_IN_SUMMARY:
        lines.append(f"...and {len(findings) - MAX_ITEMS_IN_SUMMARY} more.")

    summary = "\n".join(lines)

    first_kind, first_room, first_message = findings[0]
    mac_body = f"[{first_kind}] {_room_title(room_lookup, first_room['id'])} — {_snippet(first_message, 100)}"
    if len(findings) > 1:
        mac_body += f" (+{len(findings) - 1} more)"
    mac_notify.notify("Webex Alert", mac_body)

    if state.get("slack_user_token"):
        slack_api.post_dm(summary)

    update_state(lastCheck=new_last_check)
    return summary
