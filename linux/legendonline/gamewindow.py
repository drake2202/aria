"""
Game window — hosts the server page in Qt5 WebEngine with PepperFlash PPAPI.

Flow:
  1. Load serverlist/s{id} URL in WebEngine (with PPAPI Flash enabled)
  2. Page shows its login form (passport auth via JS)
  3. If credentials provided, auto-fill and submit login
  4. After login, page reloads → Flash game loads via PepperFlash
"""

import logging

from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QLabel,
    QMessageBox,
    QAction,
    QInputDialog,
)

from . import APP_NAME, APP_TITLE
from .config import PROXY_HOST, PROXY_PORT, LO_REGIONS, SERVER_LIST_URL
from .account_store import list_local_accounts, load_account_session
from .gameview import GameView
from .serverlist import GameServer, ServerListModel

log = logging.getLogger("gamewindow")

_MAX_LOGIN_RETRIES = 8
_LOGIN_RETRY_MS = 1200


class GameWindow(QMainWindow):
    """Game window with Flash-enabled WebEngine."""

    def __init__(self, server, email="", password="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_TITLE} — {server.display_name}")
        self.resize(1280, 800)
        self._server = server
        self._email = email
        self._password = password
        self._login_attempts = 0
        self._login_done = False

        self._game_view = GameView(account_email=email, parent=self)
        self.setCentralWidget(self._game_view)

        self._build_menubar()

        # When page finishes loading, try auto-login if credentials given
        self._game_view.page_loaded.connect(self._on_page_loaded)
        # When game frame is detected, update status and hide menu for full-screen Flash
        self._game_view.game_frame_loaded.connect(self._on_game_frame)

        self._load_server(server)

    def _build_menubar(self):
        menubar = self.menuBar()

        tools_menu = menubar.addMenu("Tools")

        proxy_action = QAction("Proxy Status", self)
        proxy_action.triggered.connect(self._show_proxy_status)
        tools_menu.addAction(proxy_action)

        tools_menu.addSeparator()

        switch_account_action = QAction("Switch Account", self)
        switch_account_action.triggered.connect(self._switch_account)
        tools_menu.addAction(switch_account_action)

        tools_menu.addSeparator()

        flash_action = QAction("Test Flash", self)
        flash_action.triggered.connect(self._test_flash)
        tools_menu.addAction(flash_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        menubar.addAction(about_action)

    def _load_server(self, server):
        region_prefix = server.region or "lopl"
        if region_prefix in LO_REGIONS:
            region_prefix = LO_REGIONS[region_prefix][1]
        url = SERVER_LIST_URL.format(subdomain=region_prefix, sid=server.server_id)
        log.info("Loading server URL: %s", url)
        self._game_view.load_url(url)

    def _on_page_loaded(self, url):
        """Called on each loadFinished — try auto-login if on the serverlist page."""
        if not self._email or not self._password:
            return
        if self._login_done or self._game_view._game_frame_detected:
            return
        if "serverlist" in url or "creaction-network" in url:
            # Wait for page JS to render the login form before injecting
            QTimer.singleShot(_LOGIN_RETRY_MS, self._try_login)

    def _try_login(self):
        if self._login_done or self._game_view._game_frame_detected:
            return
        if self._login_attempts >= _MAX_LOGIN_RETRIES:
            log.warning("Auto-login: gave up after %d attempts", _MAX_LOGIN_RETRIES)
            return
        self._login_attempts += 1
        log.info("Auto-login attempt %d/%d", self._login_attempts, _MAX_LOGIN_RETRIES)
        self._game_view.inject_login(
            self._email, self._password,
            callback=self._on_login_result,
        )

    def _on_login_result(self, ok):
        if ok:
            log.info("Auto-login: credentials injected")
            self._login_done = True
        elif not self._login_done:
            QTimer.singleShot(_LOGIN_RETRY_MS, self._try_login)

    def _on_game_frame(self, url):
        """Called when game.jsp is detected — hide chrome for full Flash view."""
        log.info("Game frame active: %s", url)
        # Hide menubar for maximum game area (like original launcher)
        self.menuBar().hide()

    def _show_proxy_status(self):
        self._game_view.load_url(f"http://{PROXY_HOST}:{PROXY_PORT}/polipo/")

    def _switch_account(self):
        accounts = list_local_accounts()
        if not accounts:
            QMessageBox.information(
                self,
                "Switch Account",
                "No local accounts found yet.\n\n"
                "Log in with another account first to create one.",
            )
            return

        labels = []
        by_label = {}
        for item in accounts:
            email = str(item.get("email", "")).strip()
            region = str(item.get("region", "")).strip() or "unknown"
            sid = int(item.get("server_id", 0) or 0)
            label = f"{email} ({region}, S{sid})"
            labels.append(label)
            by_label[label] = email

        default_index = 0
        for i, label in enumerate(labels):
            if label.lower().startswith(self._email.lower() + " "):
                default_index = i
                break

        selected, ok = QInputDialog.getItem(
            self,
            "Switch Account",
            "Select a local account:",
            labels,
            default_index,
            False,
        )
        if not ok or not selected:
            return

        selected_email = by_label[selected]
        if selected_email.strip().lower() == (self._email or "").strip().lower():
            return

        self._apply_account(selected_email)

    def _apply_account(self, email):
        region, server_id, password = load_account_session(email)
        next_server = self._resolve_server_for_account(region, server_id)
        if next_server is None:
            QMessageBox.warning(
                self,
                "Switch Account",
                f"Could not resolve saved server for {email}.\n"
                "Open the login dialog and pick the server once.",
            )
            return

        self._email = email
        self._password = password
        self._login_attempts = 0
        self._login_done = False
        self._server = next_server
        self.setWindowTitle(f"{APP_TITLE} — {self._server.display_name}")

        self._replace_game_view(email)
        self.menuBar().show()
        self._load_server(self._server)

    def _resolve_server_for_account(self, region, server_id):
        if not region or not server_id:
            return None
        model = ServerListModel()
        model.fetch(region)
        for server in model.servers:
            if server.server_id == int(server_id):
                return server
        return GameServer(
            server_id=int(server_id),
            name=f"S{server_id}",
            fullname=f"Server {server_id}",
            region=region
        )

    def _replace_game_view(self, account_email):
        old_view = self._game_view
        try:
            old_view.page_loaded.disconnect(self._on_page_loaded)
            old_view.game_frame_loaded.disconnect(self._on_game_frame)
        except Exception:
            pass

        self._game_view = GameView(account_email=account_email, parent=self)
        self.setCentralWidget(self._game_view)
        self._game_view.page_loaded.connect(self._on_page_loaded)
        self._game_view.game_frame_loaded.connect(self._on_game_frame)

        old_view.cleanup()
        old_view.deleteLater()

    def _test_flash(self):
        from .config import PEPPER_FLASH_SO
        if PEPPER_FLASH_SO.exists():
            # Navigate to chrome://plugins or a flash test page
            self._game_view.load_url("https://helpx.adobe.com/flash-player.html")
            QMessageBox.information(
                self, "Flash Plugin",
                f"PepperFlash: {PEPPER_FLASH_SO}\n\n"
                "Flash test page loaded.",
            )
        else:
            QMessageBox.warning(
                self, "Missing Flash Plugin",
                f"PepperFlash not found.\n\nExpected: {PEPPER_FLASH_SO}",
            )

    def _show_about(self):
        QMessageBox.about(
            self, "About",
            f"<h2>{APP_TITLE}</h2>"
            f"<p>Native Linux client</p>"
            f"<p>PyQt5 + Qt5 WebEngine + PepperFlash PPAPI</p>",
        )

    def closeEvent(self, event):
        # Delete the WebEngine page before the profile to avoid Qt warning
        self._game_view.cleanup()
        super().closeEvent(event)
