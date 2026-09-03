import argparse
import sys
from datetime import datetime, timezone

from . import bootstrap, cron, mac_notify, poller, webex_api, webex_auth
from .store import load_state, update_state

# Slack posting is fully implemented (bootstrap.py, slack_auth.py, slack_api.py,
# poller.py) but hidden from the active flow for now -- Splunk's workspace app
# approval can block it indefinitely for anyone, and mac notifications alone
# already cover the "don't miss a Webex DM/mention" goal with zero external
# approval needed. Flip this back to True to re-enable the Slack steps below.
SLACK_ENABLED = False


def _is_fully_set_up() -> bool:
    state = load_state()
    return bool(state.get("webexPersonId") and state.get("lastCheck"))


def cmd_setup(args: argparse.Namespace) -> None:
    print("Setting up Webex alerts (delivered as native macOS notifications).")
    print("This will open a browser tab and ask you to paste a couple of values")
    print("back here -- nothing to read elsewhere.\n")

    bootstrap.ensure_webex_app_registered()

    state = load_state()
    if args.force or not state.get("webexPersonId"):
        email = args.email or input("\nYour Cisco/Webex login email: ").strip()
        webex_auth.run_login(email)
    else:
        print(f"\nWebex already authenticated as {state.get('webexDisplayName')}, skipping (use --force to redo).")

    update_state(lastCheck=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    print("\nWatermark set to now -- only messages from this point on will alert.")

    if args.install_cron:
        cron.install()
    else:
        print("Skipping cron install (--no-cron). Run 'webex-notifier cron-install' later.")

    print("\nFiring a test macOS notification...")
    mac_notify.notify("Webex Alert", "Setup complete -- you'll get a notification like this for new DMs/mentions.")

    print("\nRunning a live test check now...")
    summary = poller.check_once()
    print(summary if summary else "No new Webex DMs/mentions right now -- that's expected, setup is complete.")
    print("\nAll set. It'll keep checking every minute on its own from here on.")


def cmd_check(args: argparse.Namespace) -> None:
    summary = poller.check_once()
    if summary:
        print(summary)
    else:
        print("No new Webex DMs or mentions since last check.")


def cmd_status(args: argparse.Namespace) -> None:
    state = load_state()
    if not state.get("webexPersonId"):
        print("Not set up yet. Run: webex-notifier setup")
        return
    print(f"Webex:       {state.get('webexDisplayName')} <{state.get('webex_email')}>")
    print(f"Last check:  {state.get('lastCheck')}")
    print(f"Cron active: {cron.is_installed()}")


def cmd_doctor(args: argparse.Namespace) -> None:
    print("Checking Webex connection...")
    webex_result = webex_api.check_connection()
    if webex_result["ok"]:
        print(f"  OK -- authenticated as {webex_result['displayName']}")
    else:
        print(f"  FAILED: {webex_result['error']}")
        if input("  Re-authenticate Webex now? [y/N] ").strip().lower() == "y":
            bootstrap.ensure_webex_app_registered()
            email = input("  Your Cisco/Webex login email: ").strip()
            webex_auth.run_login(email)

    print("Checking cron job...")
    if cron.is_installed():
        print("  OK -- installed")
    else:
        print("  MISSING")
        if input("  Install it now? [y/N] ").strip().lower() == "y":
            cron.install()


def cmd_notify_test(args: argparse.Namespace) -> None:
    fired = mac_notify.notify("Webex Alert", "Test notification -- if you see this, it works.")
    if fired:
        print("Fired. If no banner appeared, check System Settings -> Notifications -> Script Editor.")
    else:
        print("Not on macOS -- native notifications are only supported there.")


def cmd_cron_install(args: argparse.Namespace) -> None:
    cron.install()


def cmd_cron_uninstall(args: argparse.Namespace) -> None:
    cron.uninstall()


def cmd_auto(args: argparse.Namespace) -> None:
    """Default when run with no subcommand: figure out what's needed and do it."""
    if not _is_fully_set_up():
        print("Looks like this hasn't been set up yet -- starting setup.\n")
        args.email = None
        args.install_cron = True
        args.force = False
        cmd_setup(args)
    else:
        cmd_status(args)
        print("\nRun 'webex-notifier doctor' if anything above looks wrong.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="webex-notifier", description="Pop a macOS notification when a Webex DM/mention arrives.")
    sub = parser.add_subparsers(dest="command")

    p_setup = sub.add_parser("setup", help="Authenticate Webex and install the cron job.")
    p_setup.add_argument("--email", help="Cisco/Webex login email (skips the prompt).")
    p_setup.add_argument("--no-cron", dest="install_cron", action="store_false", default=True)
    p_setup.add_argument("--force", action="store_true", help="Redo auth even if already logged in.")
    p_setup.set_defaults(func=cmd_setup)

    p_check = sub.add_parser("check", help="Run one polling pass now (this is what cron calls).")
    p_check.set_defaults(func=cmd_check)

    p_status = sub.add_parser("status", help="Show current auth/cron status.")
    p_status.set_defaults(func=cmd_status)

    p_doctor = sub.add_parser("doctor", help="Diagnose and interactively fix problems.")
    p_doctor.set_defaults(func=cmd_doctor)

    p_notify_test = sub.add_parser("notify-test", help="Fire a test macOS notification.")
    p_notify_test.set_defaults(func=cmd_notify_test)

    p_cron_install = sub.add_parser("cron-install", help="(Re)install the cron job.")
    p_cron_install.set_defaults(func=cmd_cron_install)

    p_cron_uninstall = sub.add_parser("cron-uninstall", help="Remove the cron job.")
    p_cron_uninstall.set_defaults(func=cmd_cron_uninstall)

    parser.set_defaults(func=cmd_auto)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 -- top-level: friendly message beats a traceback
        print(f"\nSomething went wrong: {exc}")
        print("Run 'webex-notifier doctor' to diagnose, or re-run with --force to redo auth.")
        sys.exit(1)
