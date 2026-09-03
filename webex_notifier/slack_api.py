"""Thin wrapper over the Slack Web API used by the poller."""
import requests

from .store import load_state

POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
AUTH_TEST_URL = "https://slack.com/api/auth.test"


def auth_test() -> dict:
    """Returns {'ok': True, ...} or {'ok': False, 'error': ...} -- never raises."""
    state = load_state()
    token = state.get("slack_user_token")
    if not token:
        return {"ok": False, "error": "not_authenticated"}
    try:
        resp = requests.post(AUTH_TEST_URL, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        return resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def post_dm(text: str) -> None:
    """Sends `text` as a DM to the authenticated user's own Slack account.

    channel=<own user id> makes Slack open/reuse the self-DM automatically --
    no separate conversations.open call needed.
    """
    state = load_state()
    token = state.get("slack_user_token")
    user_id = state.get("slackUserId")
    if not token or not user_id:
        raise SystemExit("Slack is not authenticated yet. Run: webex-notifier setup")

    resp = requests.post(
        POST_MESSAGE_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": user_id, "text": text},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("ok"):
        raise SystemExit(f"Slack post failed: {payload.get('error')}")
