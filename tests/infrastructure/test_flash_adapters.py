from __future__ import annotations

from pathlib import Path

from aria.infrastructure.flash import create_flash_adapter
from aria.infrastructure.flash.linux import LinuxFlashAdapter
from aria.infrastructure.flash.macos import MacOSFlashAdapter
from aria.infrastructure.flash.windows import WindowsFlashAdapter, _resolve_arch_dir


def test_create_flash_adapter_selects_platform_adapter():
    assert isinstance(create_flash_adapter("linux"), LinuxFlashAdapter)
    assert isinstance(create_flash_adapter("darwin"), MacOSFlashAdapter)
    assert isinstance(create_flash_adapter("win32"), WindowsFlashAdapter)


def test_windows_flash_arch_override(monkeypatch):
    monkeypatch.setenv("ARIA_FLASH_ARCH", "32")
    monkeypatch.setattr("platform.machine", lambda: "AMD64")
    assert _resolve_arch_dir() == "ia32"


def test_windows_flash_plugin_path_defaults_to_x64(monkeypatch):
    monkeypatch.delenv("ARIA_FLASH_ARCH", raising=False)
    monkeypatch.setattr("platform.machine", lambda: "unknown-arch")

    adapter = WindowsFlashAdapter()
    expected_suffix = Path("flash") / "win" / "x64" / "pepflashplayer.dll"
    assert str(adapter.plugin_path()).endswith(str(expected_suffix))
