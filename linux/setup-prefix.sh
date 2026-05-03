#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

WINEPREFIX="${WINEPREFIX:-$APP_DIR/.wine-brov}"
WINEARCH="${WINEARCH:-win64}"
export WINEPREFIX WINEARCH

FLASH_OCX_WIN='Z:\\flash\\Flash64_15_0_0_167.ocx'
FLASH_OCX_HOST="$APP_DIR/flash/Flash64_15_0_0_167.ocx"
PEPPER_HOST="$APP_DIR/flash/libpepflashplayer.so"

echo "[setup] app dir:      $APP_DIR"
echo "[setup] WINEPREFIX:   $WINEPREFIX"
echo "[setup] WINEARCH:     $WINEARCH"

if ! command -v wine >/dev/null 2>&1; then
  echo "[setup] error: wine is not installed."
  echo "[setup] install: sudo pacman -S wine wine-mono wine-gecko winetricks"
  exit 1
fi

mkdir -p "$WINEPREFIX"

# Initialize prefix and wait until wineserver startup tasks complete.
wineboot -u
wineserver -w

# H2Proxy expects this cache path to exist.
mkdir -p "$WINEPREFIX/drive_c/cache/H2Proxy"

if [[ -f "$FLASH_OCX_HOST" ]]; then
  echo "[setup] registering ActiveX Flash OCX"
  wine regsvr32 /s "$FLASH_OCX_WIN" || true
else
  echo "[setup] warning: missing $FLASH_OCX_HOST"
fi

# Keep a Linux flash plugin visible for Chromium/Electron based fallback.
if [[ -f "$PEPPER_HOST" ]]; then
  mkdir -p "$WINEPREFIX/drive_c/flash"
  cp -f "$PEPPER_HOST" "$WINEPREFIX/drive_c/flash/libpepflashplayer.so"
fi

echo "[setup] done"
