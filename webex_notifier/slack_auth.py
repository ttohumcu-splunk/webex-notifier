"""Slack OAuth v2: 'Add to Slack' user-token flow against a registered Slack App.

Slack user tokens obtained this way don't expire on a fixed schedule (unless the
workspace has token rotation turned on), so no refresh cycle is needed here --
unlike Webex.
"""
import secrets
import webbrowser

import requests

from .oauth_server import wait_for_callback
from .store import load_app_config, update_state

AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.access"
USER_SCOPES = "chat:write,im:write,users:read"
REDIRECT_PORT = 8735
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/"


def run_login(slack_display_name: str) -> dict:
    app_cfg = load_app_config()
    client_id = app_cfg.get("slack_client_id")
    client_secret = app_cfg.get("slack_client_secret")
    if not client_id or not client_secret:
        raise SystemExit(
            "Missing slack_client_id/slack_client_secret in ~/.webex_notifier/app_config.json.\n"
            "Ask whoever registered the org's Slack App for this file (see README)."
        )

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "user_scope": USER_SCOPES,
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    url = AUTHORIZE_URL + "?" + requests.compat.urlencode(params)
    print(f"\nOpening your browser to connect your Slack account ({slack_display_name}) ...")
    print(f"If it doesn't open automatically, visit:\n{url}\n")
    webbrowser.open(url)

    result = wait_for_callback(REDIRECT_PORT, "Slack")
    if result.error or not result.code:
        raise SystemExit(f"Slack login failed: {result.error or 'no code received'}")
    if result.state != state:
        raise SystemExit("Slack login failed: state mismatch (possible CSRF), aborting.")

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": result.code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("ok"):
        raise SystemExit(f"Slack login failed: {payload.get('error')}")

    authed_user = payload.get("authed_user", {})
    state_update = {
        "slack_display_name": slack_display_name,
        "slack_user_token": authed_user.get("access_token"),
        "slackUserId": authed_user.get("id"),
        "slack_team_id": payload.get("team", {}).get("id"),
        "slack_team_name": payload.get("team", {}).get("name"),
    }
    if not state_update["slack_user_token"]:
        raise SystemExit(
            "Slack login succeeded but returned no user token -- check that the Slack App "
            "requests user_scope (not just bot scope) for chat:write/im:write."
        )
    update_state(**state_update)
    print(f"Slack authenticated as {slack_display_name} (team: {state_update['slack_team_name']}).")
    return state_update
