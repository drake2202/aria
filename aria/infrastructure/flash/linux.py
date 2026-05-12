"""Linux PepperFlash adapter."""

from __future__ import annotations

import logging
import os
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
    "armv7l": "armhf",
    "armv8l": "armhf",
    "aarch64": "arm64",
    "arm64": "arm64",
}


def _is_arm_arch(arch: str) -> bool:
    return arch.startswith("arm") or arch in {"aarch64", "arm64"}


def _resolve_arch_dir() -> str:
    override_raw = os.getenv("ARIA_FLASH_ARCH", "").strip().lower()
    if override_raw:
        override_map = {
            "ia32": "ia32",
            "x64": "x64",
            "arm64": "arm64",
            "armhf": "armhf",
        }
        if override_raw in {"32", "64"}:
            host_arch = platform.machine().lower()
            is_arm_host = _is_arm_arch(host_arch)
            if override_raw == "32":
                return "armhf" if is_arm_host else "ia32"
            return "arm64" if is_arm_host else "x64"
        arch_dir = override_map.get(override_raw)
        if arch_dir:
            return arch_dir
        log.warning(
            "Invalid ARIA_FLASH_ARCH='%s'; supported values: ia32, x64, arm64, armhf, 32, 64; using host auto-detection",
            override_raw,
        )

    arch = platform.machine().lower()
    arch_dir = _ARCH_MAP.get(arch)
    if arch_dir is None:
        log.warning("Unrecognized Linux architecture '%s'; defaulting to x64 flash path", arch)
        return "x64"
    return arch_dir


class LinuxFlashAdapter(FlashAdapter):
    def plugin_path(self) -> Path:
        arch_dir = _resolve_arch_dir()
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
