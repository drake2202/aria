"""Hardcoded configuration extracted from reverse-engineered binaries."""

import os
import re
import sys
from pathlib import Path


def _candidate_roots() -> list[Path]:
    """Return possible app roots for source and frozen runtime."""
    roots: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        roots.extend([exe_dir, exe_dir.parent])

    linux_dir = Path(__file__).resolve().parent.parent
    roots.append(linux_dir.parent)

    seen = set()
    unique_roots = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            unique_roots.append(root)
    return unique_roots


def _find_first(relative_path: str) -> Path:
    for root in _candidate_roots():
        p = root / relative_path
        if p.exists():
            return p
    return _candidate_roots()[0] / relative_path


def _find_flash_plugin() -> Path:
    """
    Resolve the correct bundled PepperFlash plugin for the current platform/arch.

    Bundled layout (tracked in git):
        flash/linux/x64/libpepflashplayer.so
        flash/linux/ia32/libpepflashplayer.so
        flash/mac/x64/PepperFlashPlayer.plugin/Contents/MacOS/PepperFlashPlayer

    Falls back to legacy paths for backwards compatibility.
    """
    import platform as _platform

    arch = _platform.machine().lower()
    arch_dir = "ia32" if arch in ("i386", "i686", "x86") else "x64"

    if sys.platform == "darwin":
        bundled = _find_first(
            f"flash/mac/{arch_dir}/PepperFlashPlayer.plugin/Contents/MacOS/PepperFlashPlayer"
        )
        legacy = _find_first("PepperFlashPlayer.plugin/Contents/MacOS/PepperFlashPlayer")
    else:
        bundled = _find_first(f"flash/linux/{arch_dir}/libpepflashplayer.so")
        legacy = _find_first("flash/libpepflashplayer.so")

    system_linux = Path("/usr/share/aria/flash/libpepflashplayer.so")
    xdg_linux = Path.home() / ".local" / "share" / "Aria" / "flash" / "libpepflashplayer.so"

    for candidate in [bundled, legacy, system_linux, xdg_linux]:
        if candidate.exists():
            return candidate
    return bundled


APP_DIR = _candidate_roots()[0]

MAPS_DIR = _find_first("maps")
TRANSLATIONS_DIR = _find_first("translations")
FLASH_DIR = _find_first("flash")
PEPPER_FLASH_SO = _find_flash_plugin()

# Data directory (XDG compliant or macOS specific)
if sys.platform == "darwin":
    DATA_DIR = Path.home() / "Library" / "Application Support" / "Aria"
    CACHE_DIR = Path.home() / "Library" / "Caches" / "Aria"
    CONFIG_DIR = Path.home() / "Library" / "Preferences" / "Aria"
else:
    DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Aria"
    CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "Aria"
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Aria"

SERVER_LIST_INI = CONFIG_DIR / "ServerList.ini"
REDIRECT_CACHE = CACHE_DIR / "RedirectCache.dat"


def account_key(email: str) -> str:
    """Return a stable filesystem-safe key for account-specific storage."""
    normalized = (email or "").strip().lower()
    if not normalized:
        return "default"
    safe = re.sub(r"[^a-z0-9._-]+", "_", normalized)
    return safe[:64] or "default"


def account_paths(email: str) -> dict[str, Path | str]:
    """Return per-account storage roots under XDG base dirs."""
    key = account_key(email)
    return {
        "key": key,
        "data": DATA_DIR / "accounts" / key,
        "cache": CACHE_DIR / "accounts" / key,
        "config": CONFIG_DIR / "accounts" / key,
    }

# Local proxy (matching H2Proxy behavior)
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8125

# Legend Online — all regional game codes (extracted from binary wide strings)
# Format: gamecode → (display_name, domain_prefix)
LO_REGIONS = {
    "lopl":  ("Legend Online Polska",       "lopl"),
    "lobr":  ("Legend Online Brasileiro",    "lobr"),
    "loes":  ("Legend Online Español",       "loes"),
    "lotr":  ("Legend Online Türkçe",        "lotr"),
    "lorpt": ("Legend Online Português",     "lorpt"),
    "lode":  ("Legend Online Deutsch",       "lode"),
    "loar":  ("Legend Online العربية",       "loar"),
    "lonl":  ("Legend Online Nederlands",    "lonl"),
    "losv":  ("Legend Online Svenska",       "losv"),
    "loel":  ("Legend Online Ελληνικά",      "loel"),
    "lortr": ("Legend Online Classic Türkçe", "lortr"),
    "loru":  ("Legend Online Русский",       "loru"),
}

# OAS Games server list API template (from binary: gamecode=%1)
OAS_API_URL = "https://odp3.oasgames.com/api/game/serverlist?gamecode={gamecode}"

# Server list URL template (from binary: https://%2.creaction-network.com/serverlist/s%1?pay_later=1)
SERVER_LIST_URL = "https://{subdomain}.creaction-network.com/serverlist/s{sid}?pay_later=1"

# Passport (auth) API, derived from the page JS: window.passport_url = '//passport.' + documentDomain
PASSPORT_URL = "https://passport.creaction-network.com"

# Esprit auth (used by the SmokiLogin / EGPAuth provider path)
AUTH_ENDPOINTS = {
    "esprit-login": "https://auth.espritgames.com/login",
    "esprit-register": "https://auth.espritgames.com/register",
    "esprit-social": "https://auth.espritgames.com/social",
}
ESPRIT_LOGIN_POST = "email={email}&password={password}&consumer=eslauncher-pl&locale=pl_PL&theme=all-form_launcher_v2"

# Flash game loader path (from binary: /client/Loading.swf)
LOADING_SWF = "/client/Loading.swf"

# Update and metadata
UPDATE_URL = "https://brov.site/update.php"
SERVER_MAP_URL = "https://cdn.brov.site/servermap.php"
PAYMENT_URL = "https://pay.creaction-network.com/index.html?gid=lopl&lang=pl&uid={uid}"

# Known resource servers (from binary strings)
KNOWN_RES_SERVERS = {
    "smokih5-pl-cdn": "smokih5-pl-cdn.brov.site",
}

# Map categories (from binary strings and file names)
MAP_CATEGORIES = {
    "Basic": list(range(1, 6)),
    "Advanced-Intermediate": list(range(1, 6)),
    "Expert": list(range(1, 6)),
}

# Cross-domain policy XML (from H2Proxy strings)
CROSS_DOMAIN_POLICY_XML = (
    '<?xml version="1.0"?>'
    '<cross-domain-policy>'
    '<allow-access-from domain="*" secure="false" />'
    '</cross-domain-policy>'
)

CROSS_DOMAIN_SOCKET_POLICY_XML = (
    '<cross-domain-policy>'
    '<allow-access-from domain="*" to-ports="*" />'
    '</cross-domain-policy>'
)
