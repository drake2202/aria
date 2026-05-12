"""Linux PepperFlash adapter."""

from __future__ import annotations

import logging
import platform
from pathlib import Path

from .base import FlashAdapter, _find

log = logging.getLogger("aria.flash")

# Maps platform.machine() values to bundled flash sub-directory names
_ARCH_MAP: dict[str, str] = {
    "i386": "ia32",
    "i686": "ia32",
    "x86": "ia32",
    "x86_64": "x64",
    "amd64": "x64",
    "aarch64": "arm64",
    "arm64": "arm64",
}


class LinuxFlashAdapter(FlashAdapter):
    def plugin_path(self) -> Path:
        arch = platform.machine().lower()
        arch_dir = _ARCH_MAP.get(arch)
        if arch_dir is None:
            log.warning("Unrecognised Linux architecture '%s'; defaulting to x64 flash path", arch)
            arch_dir = "x64"
        bundled = _find(f"flash/linux/{arch_dir}/libpepflashplayer.so")
        if bundled.exists():
            return bundled
        # Legacy fallback
        legacy = _find("flash/libpepflashplayer.so")
        if legacy.exists():
            return legacy
        # System install
        system = Path("/usr/share/aria/flash/libpepflashplayer.so")
        if system.exists():
            return system
        return bundled  # doesn't exist — caller handles warning

    def plugin_version(self) -> str:
        return "32.0.0.465"
