"""macOS PepperFlash adapter."""

from __future__ import annotations

import platform
from pathlib import Path

from .base import FlashAdapter, _find


class MacOSFlashAdapter(FlashAdapter):
    def plugin_path(self) -> Path:
        arch = platform.machine().lower()
        arch_dir = "x64"  # Apple Silicon runs x64 via Rosetta for Qt5
        bundled = _find(
            f"flash/mac/{arch_dir}/PepperFlashPlayer.plugin/Contents/MacOS/PepperFlashPlayer"
        )
        if bundled.exists():
            return bundled
        # Legacy root-level plugin (old install)
        legacy = _find("PepperFlashPlayer.plugin/Contents/MacOS/PepperFlashPlayer")
        if legacy.exists():
            return legacy
        return bundled

    def plugin_version(self) -> str:
        return "32.0.0.465"
