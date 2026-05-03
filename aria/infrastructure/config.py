"""Application configuration — single source of truth, no global side-effects."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _app_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # Running from source: aria/infrastructure/config.py → 3 parents up
    return Path(__file__).resolve().parent.parent.parent


APP_ROOT = _app_root()
MAPS_DIR = APP_ROOT / "maps"

# Platform-appropriate data directories
if sys.platform == "darwin":
    DATA_DIR   = Path.home() / "Library" / "Application Support" / "Aria"
    CACHE_DIR  = Path.home() / "Library" / "Caches" / "Aria"
    CONFIG_DIR = Path.home() / "Library" / "Preferences" / "Aria"
else:
    DATA_DIR   = Path(os.environ.get("XDG_DATA_HOME",   Path.home() / ".local" / "share")) / "Aria"
    CACHE_DIR  = Path(os.environ.get("XDG_CACHE_HOME",  Path.home() / ".cache"))           / "Aria"
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))           / "Aria"

SERVER_CACHE_DIR = CACHE_DIR / "servers"
REDIRECT_CACHE   = CACHE_DIR / "RedirectCache.dat"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8125

KNOWN_RES_SERVERS: dict[str, str] = {
    "smokih5-pl-cdn": "smokih5-pl-cdn.brov.site",
}

# Legend Online regions: gamecode → (display_name, domain_prefix)
LO_REGIONS: dict[str, tuple[str, str]] = {
    "lopl":  ("Legend Online Polska",         "lopl"),
    "lobr":  ("Legend Online Brasileiro",     "lobr"),
    "loes":  ("Legend Online Español",        "loes"),
    "lotr":  ("Legend Online Türkçe",         "lotr"),
    "lorpt": ("Legend Online Português",      "lorpt"),
    "lode":  ("Legend Online Deutsch",        "lode"),
    "loar":  ("Legend Online العربية",        "loar"),
    "lonl":  ("Legend Online Nederlands",     "lonl"),
    "losv":  ("Legend Online Svenska",        "losv"),
    "loel":  ("Legend Online Ελληνικά",       "loel"),
    "lortr": ("Legend Online Classic Türkçe", "lortr"),
    "loru":  ("Legend Online Русский",        "loru"),
}

OAS_API_URL       = "https://odp3.oasgames.com/api/game/serverlist?gamecode={gamecode}"
SERVER_LIST_URL   = "https://{subdomain}.creaction-network.com/serverlist/s{sid}?pay_later=1"
PASSPORT_URL      = "https://passport.creaction-network.com"
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

MAP_CATEGORIES = {
    "Basic":                list(range(1, 6)),
    "Advanced-Intermediate": list(range(1, 6)),
    "Expert":               list(range(1, 6)),
}


def account_key(email: str) -> str:
    """Return a stable filesystem-safe key for account-specific storage."""
    normalized = (email or "").strip().lower()
    if not normalized:
        return "default"
    safe = re.sub(r"[^a-z0-9._-]+", "_", normalized)
    return safe[:64] or "default"


def account_paths(email: str) -> dict[str, Path]:
    """Return per-account storage roots."""
    key = account_key(email)
    return {
        "key":    key,
        "data":   DATA_DIR   / "accounts" / key,
        "cache":  CACHE_DIR  / "accounts" / key,
        "config": CONFIG_DIR / "accounts" / key,
    }
