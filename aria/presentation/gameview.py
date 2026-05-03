"""
Game view widget — embeds game content using Qt5 WebEngine with PepperFlash PPAPI.

Qt 5.15 ships with Chromium 83 which fully supports PPAPI Flash plugins.
The original Windows launcher uses QAxWidget (ActiveX Flash) with WebView2
fallback; on Linux we use Chromium's native PPAPI path instead.

Architecture:
  - We load the serverlist page to handle login/auth normally.
  - Once game.jsp is detected in an iframe, we extract the session tokens
    (user, key, site) from the URL — they are plain query params, no server state.
  - We then serve our own minimal HTML locally via setHtml(), which embeds
    Loading.swf directly at 100%×100% with wmode=direct.
  - This bypasses the topbar, resize clamping (1000–1500px), and all overlays
    from the server's HTML shell entirely.
"""

import logging
import os
import sys

from PyQt5.QtCore import QUrl, pyqtSignal, Qt
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineScript,
)
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from aria.infrastructure.config import account_paths, account_key

log = logging.getLogger("aria.gameview")

class GamePage(QWebEnginePage):
    """Custom page: blocks Flash download redirects, logs JS console."""

    flash_call = pyqtSignal(str)

    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def javaScriptConsoleMessage(self, level, message, line, source):
        log.debug("[JS %s:%d] %s", source, line, message)

    def acceptNavigationRequest(self, url, nav_type, is_main):
        url_str = url.toString()
        if "fpdownload.macromedia.com" in url_str:
            log.info("Blocked Flash download redirect: %s", url_str)
            return False
        return True


class GameView(QWidget):
    """Widget embedding Flash game content via Qt5 WebEngine + PepperFlash PPAPI."""

    # Emitted when the game frame is active and Flash is rendering
    game_frame_loaded = pyqtSignal(str)
    # Emitted on every loadFinished with the page URL
    page_loaded = pyqtSignal(str)

    def __init__(self, account_email: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        account = account_paths(account_email)
        account_cache = account["cache"]
        account_data = account["data"]
        account_cache.mkdir(parents=True, exist_ok=True)
        account_data.mkdir(parents=True, exist_ok=True)

        profile_name = f"Aria-{account_key(account_email)}"
        # Per-account profile to isolate cookies/session data across users.
        self._profile = QWebEngineProfile(profile_name, self)
        self._profile.setCachePath(str(account_cache / "webengine-cache"))
        self._profile.setPersistentStoragePath(str(account_data / "webengine-data"))
        self._profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self._profile.setHttpCacheMaximumSize(1024 * 1024 * 1024)  # 1 GB for heavy Flash assets
        self._profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)

        # Enable Flash/plugins on profile settings
        settings = self._profile.settings()
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)

        # Also enable globally
        global_settings = QWebEngineSettings.globalSettings()
        global_settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)

        self._page = GamePage(self._profile, self)
        self._view = QWebEngineView(self)
        self._view.setPage(self._page)
        # Disable right-click context menu — Flash handles its own
        self._view.setContextMenuPolicy(Qt.NoContextMenu)
        layout.addWidget(self._view)

        self._page.loadFinished.connect(self._on_load_finished)
        self._game_frame_detected = False

    def cleanup(self):
        """Delete page before profile to prevent Qt warning on exit."""
        self._page.loadFinished.disconnect(self._on_load_finished)
        self._view.setPage(None)
        self._page.deleteLater()
        self._page = None

    def load_url(self, url: str):
        log.info("Loading URL: %s", url)
        self._view.load(QUrl(url))

    def inject_login(self, email: str, password: str, callback=None):
        """Auto-fill and submit login on the serverlist page.
        callback(bool) is called with True if fields were found, False otherwise."""
        import json
        js = """
        (function() {
            var emailField = document.getElementById('user_email');
            var pwdField = document.getElementById('user_password');
            if (emailField && pwdField) {
                emailField.value = %s;
                pwdField.value = %s;
                if (typeof ajax_login === 'function') {
                    ajax_login();
                }
                return true;
            }
            return false;
        })();
        """ % (json.dumps(email), json.dumps(password))
        if callback:
            self._page.runJavaScript(js, callback)
        else:
            self._page.runJavaScript(js)

    def _on_load_finished(self, ok):
        if not ok:
            log.warning("Page load failed")
            return

        current_url = self._page.url().toString()
        log.info("Page loaded: %s", current_url)
        self.page_loaded.emit(current_url)

        # Once game frame is detected, ignore all subsequent navigations
        # (game.jsp itself may trigger sub-navigations internally)
        if self._game_frame_detected:
            return

        # Look for the game.jsp iframe in the current page and make it fullscreen
        self._try_maximize_game_iframe()

    def _try_maximize_game_iframe(self):
        """
        Find the game.jsp iframe in the outer serverlist page and force it
        to cover the entire viewport via position:fixed + z-index.

        We stay on the serverlist page — game.jsp MUST remain inside its iframe
        because shenqu.js calls parent.* functions for authentication.
        The iframe covers the topbar visually. Clicks go naturally to the iframe
        and through to Flash — no pointer-events manipulation needed.
        """
        js = """
        (function() {
            var iframes = document.querySelectorAll('iframe');
            for (var i = 0; i < iframes.length; i++) {
                var src = iframes[i].src || iframes[i].getAttribute('src') || '';
                if (src.indexOf('game.jsp') !== -1) {
                    var f = iframes[i];
                    f.style.position = 'fixed';
                    f.style.top = '0';
                    f.style.left = '0';
                    f.style.width = '100%';
                    f.style.height = '100%';
                    f.style.zIndex = '2147483647';
                    f.style.border = 'none';
                    f.style.margin = '0';
                    f.style.padding = '0';
                    document.documentElement.style.overflow = 'hidden';
                    document.body.style.overflow = 'hidden';
                    return src;
                }
            }
            return '';
        })();
        """
        self._page.runJavaScript(js, self._on_iframe_maximized)

    def _on_iframe_maximized(self, result):
        if not result:
            log.debug("No game.jsp iframe found yet — will retry on next load")
            return
        log.info("game.jsp iframe maximized — waiting for Flash to settle: %s", result)
        self._game_frame_detected = True
        # Short delay: let Flash initialize and the iframe paint before we
        # hide the menubar and signal the window to finalize the layout.
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(800, lambda: self.game_frame_loaded.emit(result))
