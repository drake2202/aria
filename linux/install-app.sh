#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="aria"
APP_TITLE="Aria"

XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APPLICATIONS_DIR="$XDG_DATA_HOME/applications"
BIN_DIR="${HOME}/.local/bin"

DESKTOP_FILE="$APPLICATIONS_DIR/${APP_NAME}.desktop"
LAUNCHER_FILE="$BIN_DIR/${APP_NAME}"
DIST_BINARY="$SCRIPT_DIR/dist/${APP_NAME}"
SOURCE_RUNNER="$SCRIPT_DIR/run.sh"

mkdir -p "$APPLICATIONS_DIR" "$BIN_DIR"

install_binary_launcher() {
    install -Dm755 "$DIST_BINARY" "$LAUNCHER_FILE"
    echo "[install-app] Installed binary launcher to $LAUNCHER_FILE"
}

install_source_launcher() {
    cat > "$LAUNCHER_FILE" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$SOURCE_RUNNER" "\$@"
EOF
    chmod 755 "$LAUNCHER_FILE"
    echo "[install-app] Installed source launcher to $LAUNCHER_FILE"
}

if [[ -x "$DIST_BINARY" ]]; then
    install_binary_launcher
    launch_mode="binary"
else
    if [[ ! -x "$SOURCE_RUNNER" ]]; then
        echo "[install-app] ERROR: missing launcher at $SOURCE_RUNNER" >&2
        exit 1
    fi
    install_source_launcher
    launch_mode="source"
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_TITLE
Comment=Linux-native Legend Online client
Exec=$LAUNCHER_FILE
Terminal=false
Categories=Game;
StartupNotify=true
StartupWMClass=Aria
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

echo "[install-app] Installed desktop entry to $DESKTOP_FILE"
echo "[install-app] Launch mode: $launch_mode"
echo "[install-app] Aria should now appear in Rofi drun and XFCE menus"

if [[ "$launch_mode" == "source" ]]; then
    echo "[install-app] Note: this launcher points to this repo checkout. Re-run the installer if you move the repo."
fi