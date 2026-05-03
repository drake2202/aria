"""Abstract FlashAdapter — platform-specific PPAPI plugin resolution."""

from __future__ import annotations

import logging
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path

log = logging.getLogger("aria.flash")


class FlashAdapter(ABC):
    """Strategy: resolve the correct PepperFlash plugin for the host OS/arch."""

    @abstractmethod
    def plugin_path(self) -> Path:
        """Absolute path to the PPAPI plugin binary."""

    @abstractmethod
    def plugin_version(self) -> str:
        """Flash version string to report to Chromium."""

    def chromium_flags(self) -> list[str]:
        path = str(self.plugin_path())
        return [
            f"--ppapi-flash-path={path}",
            f"--ppapi-flash-version={self.plugin_version()}",
            "--allow-outdated-plugins",
            "--enable-plugins",
            "--no-sandbox",
            "--force-device-scale-factor=1",
            "--enable-gpu-rasterization",
            "--enable-zero-copy",
            "--ignore-gpu-blocklist",
            "--disable-gpu-driver-bug-workarounds",
            "--enable-native-gpu-memory-buffers",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ]

    def configure(self) -> None:
        """
        Inject Chromium flags into sys.argv and env.
        MUST be called before QApplication is created.
        """
        if not self.plugin_path().exists():
            log.warning("PepperFlash not found at %s", self.plugin_path())
            return

        # HiDPI scaling must be 1 — Flash text renders oversized otherwise
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
        os.environ["QT_SCALE_FACTOR"] = "1"
        os.environ.setdefault("QT_SCREEN_SCALE_FACTORS", "1")

        flags = self.chromium_flags()
        for flag in flags:
            if flag not in sys.argv:
                sys.argv.append(flag)
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flags)

        log.info("PepperFlash configured: %s", self.plugin_path())


def _app_root() -> Path:
    """Return the root of the aria repo (where flash/ lives)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # Running from source: aria/infrastructure/flash/base.py → 4 parents up
    return Path(__file__).resolve().parent.parent.parent.parent


def _find(relative: str) -> Path:
    root = _app_root()
    p = root / relative
    return p if p.exists() else root / relative  # always return a Path
