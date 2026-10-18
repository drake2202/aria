"""
Game window — hosts the server page in Qt5 WebEngine with PepperFlash PPAPI.

Flow:
  1. Load serverlist/s{id} URL in WebEngine (with PPAPI Flash enabled)
  2. Page shows its login form (passport auth via JS)
  3. If credentials provided, auto-fill and submit login
  4. After login, page reloads → Flash game loads via PepperFlash
"""

import logging

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QAction,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QToolBar,
    QMessageBox,
    QMenu,
)

APP_TITLE = "Aria — Legend Online"

from aria.domain.models import GameServer
from aria.infrastructure.account_store import (
    list_local_accounts,
    load_account_session,
    load_bookmarks,
    save_bookmarks,
)
from aria.infrastructure.browser import normalize_user_url
from aria.infrastructure.config import (
    LO_REGIONS,
    PROXY_HOST,
    PROXY_PORT,
    SERVER_CACHE_DIR,
    SERVER_LIST_URL,
)
from aria.infrastructure.flash import create_flash_adapter
from aria.infrastructure.serverlist import CachedServerRepository
from aria.presentation.gameview import GameView
from aria.presentation.login_dialog import LoginDialog

log = logging.getLogger("aria.gamewindow")

_MAX_LOGIN_RETRIES = 8
_LOGIN_RETRY_MS = 1200


class GameWindow(QMainWindow):
    """Game window with Flash-enabled WebEngine."""

    def __init__(self, server=None, email="", password="", launcher=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.resize(1280, 800)
        self._server = server
        self._email = email
        self._password = password
        self._login_attempts = 0
        self._login_done = False
        self._bookmarks: list[dict[str, str]] = load_bookmarks(self._email)

        self._game_view = GameView(account_email=email, parent=self)
        self.setCentralWidget(self._game_view)
        self._build_toolbar()

        self._build_menubar()

        # When page finishes loading, try auto-login if credentials given
        self._game_view.page_loaded.connect(self._on_page_loaded)
        self._game_view.load_failed.connect(self._on_load_failed)
        # When game frame is detected, update status and hide menu for full-screen Flash
        self._game_view.game_frame_loaded.connect(self._on_game_frame)

        if server:
            self._load_server(server)
        else:
            self._game_view.load_blank_page()

    def _build_menubar(self):
        menubar = self.menuBar()

        game_menu = menubar.addMenu("Game")
        open_login_action = QAction("Open Login / Server Picker", self)
        open_login_action.triggered.connect(self._open_login_dialog)
        game_menu.addAction(open_login_action)

        tools_menu = menubar.addMenu("Tools")

        proxy_action = QAction("Proxy Status", self)
        proxy_action.triggered.connect(self._show_proxy_status)
        tools_menu.addAction(proxy_action)

        tools_menu.addSeparator()

        switch_account_action = QAction("Switch Account", self)
        switch_account_action.triggered.connect(self._switch_account)
        tools_menu.addAction(switch_account_action)

        tools_menu.addSeparator()

        clear_cache_action = QAction("Clear Browser Data", self)
        clear_cache_action.triggered.connect(self._clear_browser_data)
        tools_menu.addAction(clear_cache_action)

        tools_menu.addSeparator()

        flash_action = QAction("Test Flash", self)
        flash_action.triggered.connect(self._test_flash)
        tools_menu.addAction(flash_action)

        self._bookmarks_menu = menubar.addMenu("Bookmarks")
        add_bookmark_action = QAction("Add Current Page...", self)
        add_bookmark_action.triggered.connect(self._add_bookmark)
        self._bookmarks_menu.addAction(add_bookmark_action)
        self._bookmarks_menu.addSeparator()
        self._bookmarks_items_menu = QMenu("Open Saved Bookmark", self)
        self._bookmarks_menu.addMenu(self._bookmarks_items_menu)
        self._refresh_bookmarks_menu()

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        menubar.addAction(about_action)

    def _build_toolbar(self):
        nav = QToolBar("Navigation", self)
        nav.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, nav)

        back_action = QAction("←", self)
        back_action.triggered.connect(self._game_view.navigate_back)
        nav.addAction(back_action)

        forward_action = QAction("→", self)
        forward_action.triggered.connect(self._game_view.navigate_forward)
        nav.addAction(forward_action)

        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(self._game_view.navigate_reload)
        nav.addAction(reload_action)

        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self._game_view.navigate_stop)
        nav.addAction(stop_action)

        home_action = QAction("Home", self)
        home_action.triggered.connect(self._go_home)
        nav.addAction(home_action)

        self._address_bar = QLineEdit(self)
        self._address_bar.setPlaceholderText("Enter URL (http:// or https://)")
        self._address_bar.returnPressed.connect(self._navigate_from_bar)
        nav.addWidget(self._address_bar)

        go_action = QAction("Go", self)
        go_action.triggered.connect(self._navigate_from_bar)
        nav.addAction(go_action)

    def _load_server(self, server):
        region_prefix = server.region or "lopl"
        if region_prefix in LO_REGIONS:
            region_prefix = LO_REGIONS[region_prefix][1]
        url = SERVER_LIST_URL.format(subdomain=region_prefix, sid=server.server_id)
        self.setWindowTitle(f"{APP_TITLE} — {server.display_name}")
        log.info("Loading server URL: %s", url)
        self._game_view.load_url(url)

    def _on_page_loaded(self, url):
        """Called on each loadFinished — try auto-login if on the serverlist page."""
        if url == "about:blank":
            self._address_bar.setText("")
        else:
            self._address_bar.setText(url)
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
        self.statusBar().showMessage("Game frame loaded", 3000)

    def _on_load_failed(self, url):
        QMessageBox.warning(
            self,
            "Navigation failed",
            f"Failed to load:\n{url or '(unknown URL)'}\n\n"
            "Check the address and network connection.",
        )

    def _navigate_from_bar(self):
        text = self._address_bar.text()
        normalized, error = normalize_user_url(text)
        if error:
            QMessageBox.warning(self, "Invalid URL", error)
            return
        self._game_view.load_url(normalized)

    def _go_home(self):
        self._address_bar.clear()
        self._game_view.load_blank_page()

    def _clear_browser_data(self):
        self._game_view.clear_browser_data()
        self.statusBar().showMessage("Browser cache/cookies/storage cleared.", 5000)

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
        self._bookmarks = load_bookmarks(self._email)
        self._refresh_bookmarks_menu()
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
        repo = CachedServerRepository(cache_dir=SERVER_CACHE_DIR)
        server = repo.find_by_id(region, int(server_id))
        if server:
            return server
        return GameServer(
            server_id=int(server_id),
            name=f"S{server_id}",
            fullname=f"Server {server_id}",
            region=region,
        )

    def _replace_game_view(self, account_email):
        old_view = self._game_view
        try:
            old_view.page_loaded.disconnect(self._on_page_loaded)
            old_view.load_failed.disconnect(self._on_load_failed)
            old_view.game_frame_loaded.disconnect(self._on_game_frame)
        except Exception:
            pass

        self._game_view = GameView(account_email=account_email, parent=self)
        self.setCentralWidget(self._game_view)
        self._game_view.page_loaded.connect(self._on_page_loaded)
        self._game_view.load_failed.connect(self._on_load_failed)
        self._game_view.game_frame_loaded.connect(self._on_game_frame)

        old_view.cleanup()
        old_view.deleteLater()

    def _test_flash(self):
        adapter = create_flash_adapter()
        plugin = adapter.plugin_path()
        if plugin.exists():
            self._game_view.load_url("https://helpx.adobe.com/flash-player.html")
            QMessageBox.information(
                self, "Flash Plugin",
                f"PepperFlash found:\n{plugin}\n\nFlash test page loaded.",
            )
        else:
            QMessageBox.warning(
                self, "Missing Flash Plugin",
                f"PepperFlash not found.\nExpected: {plugin}",
            )

    def _open_login_dialog(self):
        picker = LoginDialog(parent=self)
        picker.server_chosen.connect(self._on_server_chosen)
        picker.exec_()

    def _on_server_chosen(self, server, email, password):
        self._server = server
        self._email = email
        self._password = password
        self._bookmarks = load_bookmarks(self._email)
        self._refresh_bookmarks_menu()
        self.menuBar().show()
        self._load_server(server)

    def _add_bookmark(self):
        current_url = self._address_bar.text().strip()
        normalized, error = normalize_user_url(current_url) if current_url else (None, "No page URL.")
        if error:
            QMessageBox.information(self, "Add Bookmark", "Navigate to a valid page before bookmarking.")
            return

        default_name = normalized.replace("https://", "").replace("http://", "")
        name, ok = QInputDialog.getText(self, "Add Bookmark", "Bookmark name:", text=default_name)
        if not ok:
            return
        title = name.strip()
        if not title:
            QMessageBox.warning(self, "Add Bookmark", "Bookmark name cannot be empty.")
            return

        self._bookmarks = [b for b in self._bookmarks if b.get("name", "").lower() != title.lower()]
        self._bookmarks.append({"name": title, "url": normalized})
        save_bookmarks(self._email, self._bookmarks)
        self._refresh_bookmarks_menu()

    def _refresh_bookmarks_menu(self):
        self._bookmarks_items_menu.clear()
        if not self._bookmarks:
            empty = QAction("(No bookmarks saved)", self)
            empty.setEnabled(False)
            self._bookmarks_items_menu.addAction(empty)
            return

        for bookmark in self._bookmarks:
            name = bookmark.get("name", "").strip()
            url = bookmark.get("url", "").strip()
            if not name or not url:
                continue
            action = QAction(name, self)
            action.triggered.connect(lambda _checked=False, target=url: self._game_view.load_url(target))
            self._bookmarks_items_menu.addAction(action)

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
