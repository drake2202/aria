"""Windows PepperFlash adapter."""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path

from .base import FlashAdapter, _find

log = logging.getLogger("aria.flash")

_ARCH_MAP: dict[str, str] = {
    "x86": "ia32",
    "i386": "ia32",
    "i686": "ia32",
    "x86_64": "x64",
    "amd64": "x64",
}


def _resolve_arch_dir() -> str:
    override_raw = os.getenv("ARIA_FLASH_ARCH", "").strip().lower()
    if override_raw:
        override_map = {
            "ia32": "ia32",
            "x64": "x64",
            "32": "ia32",
            "64": "x64",
        }
        arch_dir = override_map.get(override_raw)
        if arch_dir:
            return arch_dir
        log.warning(
            "Invalid ARIA_FLASH_ARCH='%s'; supported values: ia32, x64, 32, 64; using host auto-detection",
            override_raw,
        )

    arch = platform.machine().lower()
    arch_dir = _ARCH_MAP.get(arch)
    if arch_dir is None:
        log.warning("Unrecognized Windows architecture '%s'; defaulting to x64 flash path", arch)
        return "x64"
    return arch_dir


class WindowsFlashAdapter(FlashAdapter):
    def plugin_path(self) -> Path:
        arch_dir = _resolve_arch_dir()
        bundled = _find(f"flash/win/{arch_dir}/pepflashplayer.dll")
        if bundled.exists():
            return bundled
        return bundled

    def plugin_version(self) -> str:
        return "32.0.0.371"
