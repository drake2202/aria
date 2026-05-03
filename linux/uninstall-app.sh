#!/usr/bin/env bash
set -euo pipefail

APP_NAME="aria"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APPLICATIONS_DIR="$XDG_DATA_HOME/applications"
BIN_DIR="${HOME}/.local/bin"

DESKTOP_FILE="$APPLICATIONS_DIR/${APP_NAME}.desktop"
LAUNCHER_FILE="$BIN_DIR/${APP_NAME}"

rm -f "$DESKTOP_FILE" "$LAUNCHER_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

echo "[uninstall-app] Removed $DESKTOP_FILE"
echo "[uninstall-app] Removed $LAUNCHER_FILE"