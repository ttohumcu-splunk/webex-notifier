#!/usr/bin/env bash
# The only thing anyone needs to run. Sets up a private Python environment
# under ~/.webex_notifier via uv (bootstrapping uv itself if needed), installs
# this package into it (so the repo folder can move or be deleted later
# without breaking the cron job), and then runs the CLI. Safe to re-run any
# time -- it no-ops once installed.
#
# uv rather than a bare python3 venv + pip: uv manages its own Python
# versions (no dependency on a system python3, and no exposure to a
# machine-wide pip.conf/PIP_USER forcing "--user" installs, which fails
# inside a venv) and ignores pip's own index-mirror config, sidestepping
# corporate PyPI mirrors that reject anonymous installs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HOME/.webex_notifier/venv"
PYTHON_VERSION="3.12"
REPO_TARBALL_URL="https://github.com/ttohumcu-splunk/webex-notifier/archive/refs/heads/main.tar.gz"

if [ "${1:-}" = "upgrade" ]; then
    if [ -d "$SCRIPT_DIR/.git" ]; then
        echo "Pulling latest changes ..."
        git -C "$SCRIPT_DIR" pull
    else
        echo "No .git here (this was a zip install) -- downloading the latest copy and updating this folder in place ..."
        curl -LsSf "$REPO_TARBALL_URL" | tar -xz -C "$SCRIPT_DIR" --strip-components=1
    fi
    echo
    shift
    set -- status "$@"
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "uv (the Python env manager this uses) was not found on this Mac."
    echo "Installing uv via its official installer (a single prebuilt binary, no Xcode/Rust/Homebrew build chain needed) ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1 && command -v brew >/dev/null 2>&1; then
    echo "Official installer didn't put uv on PATH, trying Homebrew instead ..."
    brew install uv
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "uv still isn't available after install. Install it manually (https://docs.astral.sh/uv/) and re-run this script." >&2
    exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Setting up a private Python environment at $VENV_DIR (uv fetches Python $PYTHON_VERSION itself if needed) ..."
    uv venv --python "$PYTHON_VERSION" "$VENV_DIR"
fi

echo "Installing dependencies (this only does real work the first time or after an update) ..."
if ! uv pip install --quiet --python "$VENV_DIR/bin/python" "$SCRIPT_DIR" 2>/tmp/webex_notifier_uv.log; then
    echo "Default package index failed, retrying against pypi.org directly ..."
    uv pip install --quiet --index-url https://pypi.org/simple --python "$VENV_DIR/bin/python" "$SCRIPT_DIR"
fi

exec "$VENV_DIR/bin/webex-notifier" "$@"
