"""Linux PepperFlash adapter."""

from __future__ import annotations

import platform
from pathlib import Path

from .base import FlashAdapter, _find


class LinuxFlashAdapter(FlashAdapter):
    def plugin_path(self) -> Path:
        arch = platform.machine().lower()
        arch_dir = "ia32" if arch in ("i386", "i686", "x86") else "x64"
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
