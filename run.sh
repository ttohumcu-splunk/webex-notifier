#!/usr/bin/env bash
# The only thing anyone needs to run. Sets up a private Python environment
# under ~/.webex_notifier, installs/updates this package into it (so the
# repo folder can move or be deleted later without breaking the cron job),
# and then runs the CLI. Safe to re-run any time -- it no-ops once installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HOME/.webex_notifier/venv"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found on this Mac." >&2
    echo "Install it first: run 'xcode-select --install' (or install from python.org), then re-run this script." >&2
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo "python3 is too old (need 3.9+). Install a newer Python (e.g. from python.org) and re-run this script." >&2
    exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Setting up a private Python environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing dependencies (this only does real work the first time or after an update) ..."
if ! "$VENV_DIR/bin/python" -m pip install --quiet "$SCRIPT_DIR" 2>/tmp/webex_notifier_pip.log; then
    echo "Default package index failed, retrying against pypi.org directly ..."
    "$VENV_DIR/bin/python" -m pip install --quiet --index-url https://pypi.org/simple "$SCRIPT_DIR"
fi

exec "$VENV_DIR/bin/webex-notifier" "$@"
