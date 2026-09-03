# webex-notifier

Webex doesn't reliably alert you to new DMs and @mentions — especially while
you're in a meeting — nothing like Slack's notifications. This closes that
gap: a personal crontab entry (checks every minute) pops a native macOS
notification the instant one lands, with nothing else that needs to stay
open.

Slack delivery is fully implemented but currently disabled (see
[Slack (disabled for now)](#slack-disabled-for-now) below) — Splunk's
workspace requires admin approval for new Slack apps, which can block
indefinitely, so mac notifications are the only active channel right now.

## Sharing this with colleagues

Just zip/copy this folder and hand it to them, or point them at the git repo.
There's nothing sensitive in it — no shared secrets, no config, no tokens
live here. Everything personal (Webex OAuth tokens, your own Webex
Integration's client id/secret, last-check watermark) is created fresh under
`~/.webex_notifier/` on each person's own machine the first time they run it.

## Install (per person, ~2 minutes)

```bash
git clone <this repo> webex-notifier   # or copy the folder
cd webex-notifier
./run.sh
```

That's the only command anyone needs to run — works on both Apple Silicon
and Intel Macs. `run.sh` needs nothing pre-installed — it bootstraps
[`uv`](https://docs.astral.sh/uv/) via its official installer (a single
prebuilt binary per architecture, no Xcode/Rust/Homebrew build chain) if
it's not already on the machine. uv then creates a private virtualenv at
`~/.webex_notifier/venv` — fetching its own Python 3.12 for it, with no
dependency on the machine's system `python3` — and installs this package and
its one dependency into it (falling back to the public PyPI if a corporate
package mirror rejects anonymous installs). It's safe to re-run any time; it
no-ops once already installed.

With no arguments, the CLI figures out what's missing and walks you through
it interactively — no README reading required:

1. **Register your own personal Webex Integration** (one-time, ~30 seconds):
   opens developer.webex.com, tells you exactly what to fill in, and prompts
   you to paste back a Client ID/Secret. This is *not* shared between people —
   everyone registers their own, so there's no secret file to distribute.
2. Asks for your Cisco/Webex login email, opens a browser to sign in, and
   stores a refresh token (auto-renews, no re-login ever needed).
3. Sets the initial watermark to *now* (only new activity alerts, not your
   whole history).
4. Fires a test macOS notification.
5. Installs a personal crontab entry that checks every minute.

## Upgrading

```bash
cd webex-notifier   # wherever you cloned/unzipped it
./run.sh upgrade
```

Pulls the latest code (`git pull` if you cloned it, or a fresh download
unpacked in place if you started from the zip) and reinstalls it into the
existing venv. Your Webex tokens, app config, and watermark all live under
`~/.webex_notifier/`, completely separate from the repo folder, so upgrading
never touches them — no re-registering the integration, re-login, or
re-approving scopes.

## Commands

```bash
./run.sh                    # no args: self-driving setup/status, does the right thing
./run.sh upgrade            # pull the latest code and reinstall (keeps your auth/tokens)
./run.sh setup              # one-time auth + cron install
./run.sh check              # run one check right now (what cron calls)
./run.sh status             # show auth state + whether cron is installed
./run.sh doctor             # diagnose + interactively fix problems
./run.sh notify-test        # fire a one-off test notification
./run.sh cron-install       # (re)install the cron job
./run.sh cron-uninstall     # remove the cron job
```

(`webex-notifier <command>` works the same way once `~/.webex_notifier/venv/bin`
is on your PATH — `run.sh` is just the zero-setup entry point.)

Logs land in `~/.webex_notifier/monitor.log`.

If no notification banner appears, check System Settings → Notifications →
"Script Editor" (the identity `osascript` runs under) — sound can play with
the banner style set to "None", make sure it's set to Banners or Alerts.

## How detection works

- **DMs**: any new message in a 1:1 Webex space that you didn't send.
- **Mentions**: any new message in a group space where Webex's own
  `mentionedPeople` field includes you, restricted to spaces whose
  `lastActivity` is after your last check (so it doesn't have to rescan every
  space you're in — accounts with 300+ spaces error out of Webex's search API
  if you try to search across all of them at once, hence this filtered-scan
  approach).
- Messages from bot accounts (`*@webex.bot`) are ignored on both fronts.

## Slack (disabled for now)

The code for posting alerts to Slack as well (`slack_auth.py`, `slack_api.py`,
Slack app registration in `bootstrap.py`) is all still here, just switched off
via `SLACK_ENABLED = False` at the top of `webex_notifier/cli.py`. To turn it
back on (e.g. once a pending workspace app-approval request clears): flip
that flag to `True`, then run `./run.sh doctor` to finish Slack auth. Note
Slack apps in a workspace with app-approval enabled need a workspace admin to
approve the app once (per-app, not per-user) before anyone can connect it.

## Security notes

- Tokens live in `~/.webex_notifier/state.json` with `0600` permissions.
- Your personal Webex Integration's client secret lives in
  `~/.webex_notifier/app_config.json`, also `0600` and never committed —
  it's created locally by the setup wizard, not shared or distributed.
- This is a confidential OAuth client (standard Authorization Code grant with
  `client_secret`, no PKCE — Webex Integrations don't support PKCE params).
  The secret never leaves your machine except to Webex's own token endpoint.
