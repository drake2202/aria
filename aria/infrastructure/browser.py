"""Helpers for browser-style navigation."""

from __future__ import annotations

from urllib.parse import urlparse


def normalize_user_url(value: str) -> tuple[str | None, str | None]:
    """Normalize a user-entered address to an absolute HTTP(S) URL."""
    raw = (value or "").strip()
    if not raw:
        return None, "Please enter a URL."

    candidate = raw
    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return None, "Only HTTP and HTTPS URLs are supported."
    if not parsed.netloc:
        return None, "Invalid URL. Please enter a full host name."
    return candidate, None
