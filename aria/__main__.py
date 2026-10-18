"""
Aria Launcher — entry point.

Boot sequence:
  1. Select platform FlashAdapter, call configure() BEFORE any Qt import
  2. Build infrastructure (credential store, server repo, cache dirs)
  3. Wire domain service via DI
  4. Start H2Proxy background thread
  5. Show browser-style GameWindow (login/server picker available from menu)
"""

import asyncio
import logging
import os
import signal
import sys
import threading
from pathlib import Path

from aria.infrastructure.flash import create_flash_adapter

# ── Flash flags and Qt Env MUST be configured before any Qt import ─────────────
if sys.platform == "darwin":
    # Required for QtWebEngine inside PyInstaller .app bundle on macOS
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
    os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
_flash = create_flash_adapter()
_flash.configure()
# ─────────────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import QApplication  # noqa: E402

from aria.domain.services import LauncherService  # noqa: E402
from aria.infrastructure.config import (  # noqa: E402
    CACHE_DIR,
    CONFIG_DIR,
    DATA_DIR,
    SERVER_CACHE_DIR,
)
from aria.infrastructure.credentials import SystemCredentialStore  # noqa: E402
from aria.infrastructure.h2proxy import H2Proxy  # noqa: E402
from aria.infrastructure.serverlist import CachedServerRepository  # noqa: E402
from aria.presentation.gamewindow import GameWindow  # noqa: E402
from aria.presentation.stylesheet import GAME_WINDOW_STYLE  # noqa: E402

APP_NAME  = "Aria"
APP_TITLE = "Aria — Legend Online"

log = logging.getLogger("aria")

if sys.platform == "win32":
    _MMS_CFG = (
        Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        / "Macromedia"
        / "Flash Player"
        / "mms.cfg"
    )
else:
    _MMS_CFG = Path.home() / ".macromedia" / "mms.cfg"
_MMS_CONTENT = """\
EOLUninstallDisable=1
SilentAutoUpdateEnable=0
AutoUpdateDisable=1
AllowListURLPattern=*
EnableAllowList=1
ErrorReportingEnable=0
"""

# Single-instance lock (Unix only)
_LOCK_FD = None


def _ensure_mms_cfg() -> None:
    if _MMS_CFG.exists():
        return
    try:
        _MMS_CFG.parent.mkdir(parents=True, exist_ok=True)
        _MMS_CFG.write_text(_MMS_CONTENT)
        log.info("Created Flash mms.cfg: %s", _MMS_CFG)
    except OSError as e:
        log.warning("Could not create mms.cfg: %s", e)


def _acquire_lock() -> bool:
    global _LOCK_FD
    if sys.platform == "win32":
        return True  # No fcntl on Windows — skip
    import fcntl
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = DATA_DIR / "instance.lock"
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        _LOCK_FD = fd
        return True
    except OSError:
        fd.close()
        return False


def _run_proxy(proxy: H2Proxy) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(proxy.start())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(proxy.stop())
        loop.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s",
    )

    for d in (DATA_DIR, CACHE_DIR, CONFIG_DIR, SERVER_CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)

    _ensure_mms_cfg()

    if not _acquire_lock():
        print(f"{APP_NAME} is already running.", file=sys.stderr)
        sys.exit(1)

    log.info("Starting %s (PyQt5 + PepperFlash, platform=%s)", APP_NAME, sys.platform)

    # ── Infrastructure ───────────────────────────────────────────────────────
    credential_store = SystemCredentialStore()
    server_repo      = CachedServerRepository(cache_dir=SERVER_CACHE_DIR)

    # ── Domain service (DI) ──────────────────────────────────────────────────
    launcher = LauncherService(server_repo, credential_store)

    # ── H2Proxy background thread ────────────────────────────────────────────
    proxy = H2Proxy()
    proxy_thread = threading.Thread(target=_run_proxy, args=(proxy,), daemon=True)
    proxy_thread.start()
    log.info("H2Proxy thread started")

    # ── Qt application ───────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(GAME_WINDOW_STYLE)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    game_window = GameWindow(server=None, email="", password="", launcher=launcher)
    game_window.show()

    exit_code = app.exec_()
    log.info("Shutting down")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
