"""Flash adapter selection helpers."""

from __future__ import annotations

import sys

from .base import FlashAdapter
from .linux import LinuxFlashAdapter
from .macos import MacOSFlashAdapter
from .windows import WindowsFlashAdapter


def create_flash_adapter(platform_name: str | None = None) -> FlashAdapter:
    platform_name = platform_name or sys.platform
    if platform_name == "darwin":
        return MacOSFlashAdapter()
    if platform_name == "win32":
        return WindowsFlashAdapter()
    return LinuxFlashAdapter()
