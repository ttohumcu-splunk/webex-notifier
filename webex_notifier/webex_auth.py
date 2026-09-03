"""Webex OAuth: standard Authorization Code grant against a registered Webex
Integration (a confidential client -- Webex issues a client_secret, and its
/authorize endpoint doesn't document or support PKCE params, so this uses the
client_secret-based exchange straight from Webex's own integration docs).

Access tokens last ~14 days, refresh tokens ~90 days and are rotated on use, so a
refresh (see get_valid_access_token) keeps a cron job authenticated indefinitely
without any human re-approving anything.
"""
import secrets
import time
import webbrowser

import requests

from .oauth_server import wait_for_callback
from .store import load_app_config, load_state, update_state

AUTH_URL = "https://webexapis.com/v1/authorize"
TOKEN_URL = "https://webexapis.com/v1/access_token"
ME_URL = "https://webexapis.com/v1/people/me"
SCOPES = "spark:messages_read spark:rooms_read spark:people_read"
REDIRECT_PORT = 8734
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/"


def run_login(cisco_email: str) -> dict:
    app_cfg = load_app_config()
    client_id = app_cfg.get("webex_client_id")
    client_secret = app_cfg.get("webex_client_secret")
    if not client_id or not client_secret:
        raise SystemExit(
            "Missing webex_client_id/webex_client_secret in ~/.webex_notifier/app_config.json.\n"
            "Run 'webex-notifier setup' to register your own Webex Integration first."
        )

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    }
    url = AUTH_URL + "?" + requests.compat.urlencode(params)
    print(f"\nOpening your browser to sign in to Webex as {cisco_email} ...")
    print(f"If it doesn't open automatically, visit:\n{url}\n")
    webbrowser.open(url)

    result = wait_for_callback(REDIRECT_PORT, "Webex")
    if result.error or not result.code:
        raise SystemExit(f"Webex login failed: {result.error or 'no code received'}")
    if result.state != state:
        raise SystemExit("Webex login failed: state mismatch (possible CSRF), aborting.")

    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": result.code,
        "redirect_uri": REDIRECT_URI,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()

    access_token = tokens["access_token"]
    me = requests.get(ME_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    me.raise_for_status()
    me_json = me.json()

    now = int(time.time())
    state_update = {
        "webex_email": cisco_email,
        "webex_access_token": access_token,
        "webex_refresh_token": tokens.get("refresh_token"),
        "webex_token_expires_at": now + int(tokens.get("expires_in", 0)),
        "webexPersonId": me_json.get("id"),
        "webexDisplayName": me_json.get("displayName"),
    }
    update_state(**state_update)
    print(f"Webex authenticated as {me_json.get('displayName')} ({cisco_email}).")
    return state_update


def get_valid_access_token() -> str:
    """Returns a live access token, refreshing it first if it's expired or near-expiry."""
    state = load_state()
    access_token = state.get("webex_access_token")
    refresh_token = state.get("webex_refresh_token")
    expires_at = state.get("webex_token_expires_at", 0)

    if not access_token or not refresh_token:
        raise SystemExit("Webex is not authenticated yet. Run: webex-notifier setup")

    if time.time() < expires_at - 300:
        return access_token

    app_cfg = load_app_config()
    data = {
        "grant_type": "refresh_token",
        "client_id": app_cfg.get("webex_client_id"),
        "client_secret": app_cfg.get("webex_client_secret"),
        "refresh_token": refresh_token,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    tokens = resp.json()

    now = int(time.time())
    update_state(
        webex_access_token=tokens["access_token"],
        webex_refresh_token=tokens.get("refresh_token", refresh_token),
        webex_token_expires_at=now + int(tokens.get("expires_in", 0)),
    )
    return tokens["access_token"]
