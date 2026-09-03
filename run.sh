#!/usr/bin/env bash
# The only thing anyone needs to run. Sets up a private Python environment
# under ~/.webex_notifier, installs/updates this package into it (so the
# repo folder can move or be deleted later without breaking the cron job),
# and then runs the CLI. Safe to re-run any time -- it no-ops once installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HOME/.webex_notifier/venv"

python_ok() {
    command -v python3 >/dev/null 2>&1 && \
        python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'
}

if ! python_ok; then
    echo "python3 3.9+ was not found on this Mac."
    read -r -p "Install it now via Homebrew? [y/N] " reply || reply=""
    case "$reply" in
        [yY]|[yY][eE][sS])
            if ! command -v brew >/dev/null 2>&1; then
                echo "Homebrew not found either -- installing Homebrew first ..."
                NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                if [ -x /opt/homebrew/bin/brew ]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                elif [ -x /usr/local/bin/brew ]; then
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
            fi
            echo "Installing python3 via Homebrew ..."
            brew install python3
            ;;
        *)
            echo "Install it yourself: run 'xcode-select --install' (or install from python.org), then re-run this script." >&2
            exit 1
            ;;
    esac
fi

if ! python_ok; then
    echo "python3 3.9+ still isn't available after install. Install it manually and re-run this script." >&2
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
