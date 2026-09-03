"""Interactive first-run wizard: walks a human through registering the org's
Webex Integration and Slack App (once, ever) and per-user OAuth login, opening
each required browser page and capturing pasted values -- no README reading.
"""
import getpass
import webbrowser

from .store import load_app_config, save_app_config

WEBEX_NEW_INTEGRATION_URL = "https://developer.webex.com/my-apps/new/integration"
SLACK_NEW_APP_URL = "https://api.slack.com/apps?new_app=1"


def _prompt_required(label: str, hidden: bool = False) -> str:
    while True:
        value = (getpass.getpass(f"{label}: ") if hidden else input(f"{label}: ")).strip()
        if value:
            return value
        print("  (can't be empty, try again)")


def ensure_webex_app_registered() -> dict:
    app_cfg = load_app_config()
    if app_cfg.get("webex_client_id") and app_cfg.get("webex_client_secret"):
        print("Webex Integration already configured, skipping registration.")
        return app_cfg

    print("\n=== Step 1: Register your own Webex Integration (one-time, ~30 seconds) ===")
    print("Opening developer.webex.com/my-apps ...")
    webbrowser.open(WEBEX_NEW_INTEGRATION_URL)
    print(
        "\nIn the page that just opened:\n"
        "  1. Name it anything, e.g. 'Webex Mac Alerts'.\n"
        "  2. Icon: pick any, doesn't matter.\n"
        "  3. Redirect URI: http://localhost:8734/\n"
        "  4. Scopes: check spark:messages_read, spark:rooms_read, spark:people_read\n"
        "  5. Click 'Add Integration'.\n"
        "You'll land on a page showing a Client ID and Client Secret.\n"
    )
    input("Press Enter once you're looking at that page... ")
    client_id = _prompt_required("Paste the Client ID")
    client_secret = _prompt_required("Paste the Client Secret", hidden=True)

    app_cfg["webex_client_id"] = client_id
    app_cfg["webex_client_secret"] = client_secret
    save_app_config(app_cfg)
    print("Saved to ~/.webex_notifier/app_config.json on this machine -- never needed again here.")
    return app_cfg


def ensure_slack_app_registered() -> dict:
    app_cfg = load_app_config()
    if app_cfg.get("slack_client_id") and app_cfg.get("slack_client_secret"):
        print("Slack App already configured, skipping registration.")
        return app_cfg

    print("\n=== Step 2: Register a Slack App (one-time, for everyone in the org) ===")
    print("Opening api.slack.com/apps ...")
    webbrowser.open(SLACK_NEW_APP_URL)
    print(
        "\nIn the page that just opened:\n"
        "  1. Choose 'From scratch'.\n"
        "  2. Name it anything, e.g. 'Webex Alert Bridge'; pick your workspace.\n"
        "  3. Once created, go to 'OAuth & Permissions' in the left sidebar.\n"
        "  4. Under 'Redirect URLs' add: http://localhost:8735/  -- then Save URLs.\n"
        "  5. Under 'User Token Scopes' add: chat:write, im:write, users:read\n"
        "  6. Go to 'Basic Information' in the left sidebar to find the Client ID/Secret.\n"
    )
    input("Press Enter once you're looking at Basic Information... ")
    client_id = _prompt_required("Paste the Client ID")
    client_secret = _prompt_required("Paste the Client Secret", hidden=True)

    app_cfg["slack_client_id"] = client_id
    app_cfg["slack_client_secret"] = client_secret
    save_app_config(app_cfg)
    print("Saved. This step never needs to happen again for anyone else in the org --")
    print("just share the resulting ~/.webex_notifier/app_config.json file with them.")
    return app_cfg


def is_app_configured() -> bool:
    app_cfg = load_app_config()
    return bool(
        app_cfg.get("webex_client_id")
        and app_cfg.get("webex_client_secret")
        and app_cfg.get("slack_client_id")
        and app_cfg.get("slack_client_secret")
    )
