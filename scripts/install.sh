#!/bin/bash
# Aria — distro-aware dependency installer
#
# Detects the Linux distribution via /etc/os-release and installs the required
# system packages using the appropriate package manager, then creates a Python
# virtual environment and installs the Python dependencies.
#
# Supported package managers: apt, dnf, yum, pacman, zypper, apk
#
# Usage:
#   bash scripts/install.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=10

# ---------------------------------------------------------------------------
# Python version check
# ---------------------------------------------------------------------------
check_python_version() {
    if ! command -v python3 &>/dev/null; then
        echo "Error: python3 not found. Please install Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ first." >&2
        exit 1
    fi
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$PY_MAJOR" -lt "$PYTHON_MIN_MAJOR" ] || \
       { [ "$PY_MAJOR" -eq "$PYTHON_MIN_MAJOR" ] && [ "$PY_MINOR" -lt "$PYTHON_MIN_MINOR" ]; }; then
        echo "Error: Python ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ is required (found ${PY_VERSION})." >&2
        exit 1
    fi
    echo "Python version: ${PY_VERSION} ✓"
}

# ---------------------------------------------------------------------------
# Distro detection
# ---------------------------------------------------------------------------
detect_distro() {
    local distro="unknown"
    if [ -f /etc/os-release ]; then
        # shellcheck source=/dev/null
        . /etc/os-release
        distro="${ID:-unknown}"
    elif command -v lsb_release &>/dev/null; then
        distro="$(lsb_release -si | tr '[:upper:]' '[:lower:]')"
    fi

    case "$distro" in
        ubuntu|debian|linuxmint|pop|zorin|elementary|neon|kali|parrot|\
        fedora|rhel|centos|almalinux|rocky|ol|\
        arch|manjaro|endeavouros|garuda|artix|\
        opensuse*|suse*|opensuse-leap|opensuse-tumbleweed|alpine)
            echo "$distro"
            return
            ;;
    esac

    if [ -n "${ID_LIKE:-}" ]; then
        for family in ${ID_LIKE}; do
            case "$(echo "$family" | tr '[:upper:]' '[:lower:]')" in
                debian) echo "debian"; return ;;
                rhel|fedora) echo "fedora"; return ;;
                arch) echo "arch"; return ;;
                suse) echo "opensuse"; return ;;
                alpine) echo "alpine"; return ;;
            esac
        done
    fi

    echo "$distro"
}

# ---------------------------------------------------------------------------
# System package installation
# ---------------------------------------------------------------------------
install_system_deps() {
    local distro="$1"
    echo "Detected Linux distribution: $distro"

    case "$distro" in
        ubuntu|debian|linuxmint|pop|zorin|elementary|neon|kali|parrot)
            echo "Using apt..."
            sudo apt-get update -q
            sudo apt-get install -y \
                python3 python3-pip python3-venv \
                python3-pyqt5 python3-pyqt5.qtwebengine \
                libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
                libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
                libxcb-shape0 libxcb-xkb1 libxkbcommon-x11-0 \
                libsecret-1-0 libdbus-1-3
            ;;
        fedora)
            echo "Using dnf..."
            sudo dnf install -y \
                python3 python3-pip python3-virtualenv \
                python3-pyqt5 python3-qt5-webengine \
                xcb-util-wm xcb-util-image xcb-util-keysyms \
                xcb-util-renderutil libxkbcommon-x11 \
                libsecret dbus-libs
            ;;
        rhel|centos|almalinux|rocky|ol)
            echo "Using dnf/yum..."
            PKG_MGR=$(command -v dnf 2>/dev/null || echo yum)
            sudo "$PKG_MGR" install -y \
                python3 python3-pip \
                xcb-util-wm xcb-util-image xcb-util-keysyms \
                xcb-util-renderutil libxkbcommon-x11 \
                libsecret dbus-libs
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            echo "Using pacman..."
            sudo pacman -Sy --noconfirm \
                python python-pip python-pyqt5 python-pyqtwebengine \
                xcb-util-wm xcb-util-image xcb-util-keysyms \
                xcb-util-renderutil libxkbcommon-x11 \
                libsecret dbus
            ;;
        opensuse*|suse*|opensuse-leap|opensuse-tumbleweed)
            echo "Using zypper..."
            sudo zypper install -y \
                python3 python3-pip \
                python3-qt5 python3-pyqtwebengine \
                libxcb-xinerama0 libxkbcommon-x11-0 \
                libsecret-1-0 libdbus-1-3
            ;;
        alpine)
            echo "Using apk..."
            sudo apk add --no-cache \
                python3 py3-pip \
                py3-pyqt5 \
                xcb-util-wm xcb-util-image xcb-util-keysyms \
                xcb-util-renderutil libxkbcommon-x11 \
                libsecret dbus
            ;;
        *)
            echo ""
            echo "Warning: Unknown or unsupported distribution '${distro}'."
            echo "Please install the following manually before continuing:"
            echo "  - Python 3.10+"
            echo "  - PyQt5 5.15+ and PyQtWebEngine 5.15+"
            echo "  - libxcb-xinerama, libxkbcommon-x11, libsecret, dbus"
            echo ""
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Python environment setup
# ---------------------------------------------------------------------------
setup_python_env() {
    cd "$REPO_ROOT"
    echo ""
    echo "Setting up Python virtual environment..."
    python3 -m venv .venv --system-site-packages
    # shellcheck source=/dev/null
    source .venv/bin/activate
    pip install --upgrade pip
    # Keep Qt bindings from distro packages (installed above) to avoid pip
    # attempting source builds on ARM/SBC systems.
    pip install -e . --no-deps

    # Install non-Qt runtime deps from pyproject.toml (single source of truth).
    mapfile -t non_qt_deps < <(python3 - <<'PY'
import pathlib
import re
import tomllib

pyproject = pathlib.Path("pyproject.toml")
data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
deps = data.get("project", {}).get("dependencies", [])

for dep in deps:
    pkg = re.split(r"[<>=!~\s\[]", dep, maxsplit=1)[0].lower().replace("_", "-")
    if pkg in {"pyqt5", "pyqtwebengine"}:
        continue
    print(dep)
PY
)

    if [ "${#non_qt_deps[@]}" -gt 0 ]; then
        pip install "${non_qt_deps[@]}"
    fi

    if ! python - <<'PY'
try:
    from PyQt5 import QtWebEngineWidgets  # noqa: F401
except ImportError:
    raise SystemExit(1)
PY
    then
        echo ""
        echo "Error: PyQt5/PyQtWebEngine are not available to this environment."
        echo "Install the distro packages (for Debian/Ubuntu: python3-pyqt5 python3-pyqt5.qtwebengine),"
        echo "or pip wheels on supported platforms, then re-run this script."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
ARCH=$(uname -m)
echo "Host architecture: $ARCH"

check_python_version
DISTRO=$(detect_distro)
install_system_deps "$DISTRO"
setup_python_env

echo ""
echo "Installation complete!"
echo "To start Aria, run:"
echo "  source .venv/bin/activate && python3 -m aria"
