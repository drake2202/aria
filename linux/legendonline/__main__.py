"""
Entry point — orchestrates H2Proxy, single-instance lock, and UI flow.

Flow:
  1. Configure PepperFlash PPAPI flags (BEFORE any Qt import)
  2. Single-instance lock
  3. Start H2Proxy in background thread
  4. Show LoginDialog (region + server picker)
  5. Open GameWindow with Flash-enabled WebEngine
"""

import asyncio
import fcntl
import logging
import os
import signal
import sys
import threading
from pathlib import Path

# Flash flags MUST be set before any Qt import
from .gameview import configure_flash_flags
configure_flash_flags()

from PyQt5.QtWidgets import QApplication

from . import APP_NAME
from .config import DATA_DIR, CACHE_DIR, CONFIG_DIR
from .h2proxy import H2Proxy
from .login_dialog import LoginDialog
from .gamewindow import GameWindow
from .stylesheet import LOGIN_STYLE, GAME_WINDOW_STYLE

log = logging.getLogger("legendonline")

LOCK_FILE = DATA_DIR / "instance.lock"

_MMS_CFG = Path.home() / ".macromedia" / "mms.cfg"
_MMS_CONTENT = """\
EOLUninstallDisable=1
SilentAutoUpdateEnable=0
AutoUpdateDisable=1
AllowListURLPattern=*
EnableAllowList=1
ErrorReportingEnable=0
"""


def _ensure_mms_cfg():
    """Create Flash mms.cfg if absent (EOL timebomb bypass)."""
    if _MMS_CFG.exists():
        return
    try:
        _MMS_CFG.parent.mkdir(parents=True, exist_ok=True)
        _MMS_CFG.write_text(_MMS_CONTENT)
        log.info("Created %s", _MMS_CFG)
    except OSError as e:
        log.warning("Could not create %s: %s", _MMS_CFG, e)


def _acquire_lock():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        _acquire_lock._fd = lock_fd
        return True
    except OSError:
        lock_fd.close()
        return False


def _run_proxy_thread(proxy):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(proxy.start())
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(proxy.stop())
        loop.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s",
    )

    for d in (DATA_DIR, CACHE_DIR, CONFIG_DIR):
        d.mkdir(parents=True, exist_ok=True)

    _ensure_mms_cfg()

    if not _acquire_lock():
        print(f"{APP_NAME} is already running.", file=sys.stderr)
        sys.exit(1)

    log.info("Starting %s (Linux native, PyQt5 + PepperFlash)", APP_NAME)

    # Start H2Proxy in background thread
    proxy = H2Proxy()
    proxy_thread = threading.Thread(target=_run_proxy_thread, args=(proxy,), daemon=True)
    proxy_thread.start()
    log.info("H2Proxy thread started")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(LOGIN_STYLE)

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    picker = LoginDialog()
    game_window = None

    def on_server_chosen(server, email, password):
        nonlocal game_window
        app.setStyleSheet(GAME_WINDOW_STYLE)
        game_window = GameWindow(server, email, password)
        game_window.show()

    picker.server_chosen.connect(on_server_chosen)

    if picker.exec_() != LoginDialog.Accepted:
        log.info("Server selection cancelled")
        sys.exit(0)

    if game_window is None:
        log.error("Login accepted but no game window created")
        sys.exit(1)

    exit_code = app.exec_()
    log.info("Shutting down")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
