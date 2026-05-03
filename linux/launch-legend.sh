#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

WINEPREFIX="${WINEPREFIX:-$APP_DIR/.wine-brov}"
WINEARCH="${WINEARCH:-win64}"
WINEDEBUG="${WINEDEBUG:--all}"
export WINEPREFIX WINEARCH WINEDEBUG

LEGEND_EXE="$APP_DIR/LegendOnline.exe"
H2PROXY_EXE="$APP_DIR/H2Proxy.exe"

if ! command -v wine >/dev/null 2>&1; then
  echo "[launch] error: wine is not installed"
  exit 1
fi

if [[ ! -f "$LEGEND_EXE" ]]; then
  echo "[launch] error: missing $LEGEND_EXE"
  exit 1
fi

if [[ "${1:-}" == "--init" ]]; then
  "$SCRIPT_DIR/setup-prefix.sh"
fi

cleanup() {
  # Mirrors original behavior: kill helper proxy process on close/start.
  wine cmd /C taskkill /IM H2Proxy.exe /F >/dev/null 2>&1 || true
  wineserver -w >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "[launch] app dir:    $APP_DIR"
echo "[launch] WINEPREFIX: $WINEPREFIX"

# Match the original startup flow: kill stale helper before relaunch.
wine cmd /C taskkill /IM H2Proxy.exe /F >/dev/null 2>&1 || true

if [[ -f "$H2PROXY_EXE" ]]; then
  echo "[launch] starting H2Proxy.exe"
  wine "$H2PROXY_EXE" >/dev/null 2>&1 &
  sleep 2
fi

echo "[launch] starting LegendOnline.exe"
exec wine "$LEGEND_EXE"
