#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use the venv with PyQt5 + Qt5 WebEngine (PepperFlash PPAPI support)
if [[ -f .venv/bin/python3 ]]; then
    exec .venv/bin/python3 -m legendonline "$@"
else
    echo "ERROR: venv not found. Run: python3 -m venv --system-site-packages .venv && .venv/bin/pip install PyQt5 PyQtWebEngine"
    exit 1
fi
