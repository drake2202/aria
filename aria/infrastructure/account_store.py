"""Account persistence helpers for per-account session and preferences."""

import base64
import json
import logging
from pathlib import Path

from .config import CONFIG_DIR, account_key, account_paths

log = logging.getLogger("account_store")

_ACCOUNT_STATE_FILE = CONFIG_DIR / "account_state.json"


def load_last_email() -> str:
    """Return last used email from global account state."""
    try:
        if _ACCOUNT_STATE_FILE.exists():
            data = json.loads(_ACCOUNT_STATE_FILE.read_text())
            return data.get("last_email", "")
    except Exception:
        pass
    return ""


def _session_file_for_email(email: str, create_dirs: bool = False) -> Path:
    cfg_dir = account_paths(email)["config"]
    if create_dirs:
        cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "last_server.json"


def _bookmarks_file_for_email(email: str, create_dirs: bool = False) -> Path:
    cfg_dir = account_paths(email)["config"]
    if create_dirs:
        cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "bookmarks.json"


def load_account_session(email: str) -> tuple[str, int, str]:
    """Return (region, server_id, password) for an account."""
    session_file = _session_file_for_email(email)
    try:
        if session_file.exists():
            data = json.loads(session_file.read_text())
            pwd = ""
            if data.get("pw"):
                try:
                    pwd = base64.b64decode(data["pw"]).decode()
                except Exception:
                    pass
            return data.get("region", ""), int(data.get("server_id", 0)), pwd
    except Exception:
        pass
    return "", 0, ""


def save_account_session(region: str, server_id: int, email: str, password: str) -> None:
    """Persist selected server and credentials for one account."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _ACCOUNT_STATE_FILE.write_text(json.dumps({"last_email": email}))

        session_file = _session_file_for_email(email, create_dirs=True)
        session_file.write_text(json.dumps({
            "region": region,
            "server_id": int(server_id or 0),
            "email": email,
            "account_key": account_key(email),
            "pw": base64.b64encode(password.encode()).decode() if password else "",
        }))
    except Exception as e:
        log.warning("Failed to save session: %s", e)


def list_local_accounts() -> list[dict[str, object]]:
    """Discover locally saved accounts and return metadata for account switch UI."""
    accounts_root = CONFIG_DIR / "accounts"
    result: list[dict[str, object]] = []
    if not accounts_root.exists():
        return result

    for session_file in sorted(accounts_root.glob("*/last_server.json")):
        try:
            data = json.loads(session_file.read_text())
            email = str(data.get("email", "")).strip()
            if not email:
                continue
            result.append({
                "email": email,
                "region": str(data.get("region", "")),
                "server_id": int(data.get("server_id", 0) or 0),
                "account_key": str(data.get("account_key", account_key(email))),
            })
        except Exception:
            continue

    # Deduplicate by email while preserving order.
    dedup: list[dict[str, object]] = []
    seen = set()
    for item in result:
        email = str(item.get("email", "")).lower()
        if email in seen:
            continue
        seen.add(email)
        dedup.append(item)
    return dedup


def load_bookmarks(email: str) -> list[dict[str, str]]:
    """Load per-account bookmarks from config dir."""
    bookmarks_file = _bookmarks_file_for_email(email)
    try:
        if not bookmarks_file.exists():
            return []
        raw = json.loads(bookmarks_file.read_text())
        if not isinstance(raw, list):
            return []
        bookmarks: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            url = str(item.get("url", "")).strip()
            if not name or not url:
                continue
            bookmarks.append({"name": name, "url": url})
        return bookmarks
    except Exception:
        return []


def save_bookmarks(email: str, bookmarks: list[dict[str, str]]) -> None:
    """Persist per-account bookmarks to config dir."""
    bookmarks_file = _bookmarks_file_for_email(email, create_dirs=True)
    serialized = []
    for item in bookmarks:
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        if not name or not url:
            continue
        serialized.append({"name": name, "url": url})
    bookmarks_file.write_text(json.dumps(serialized, indent=2))