"""Server picker dialog — region + server selection with optional auto-login."""

import logging
import re

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
)

from aria.infrastructure.config import LO_REGIONS, account_key, SERVER_CACHE_DIR
from aria.infrastructure.account_store import load_last_email, load_account_session, save_account_session
from aria.infrastructure.serverlist import CachedServerRepository
from aria.domain.models import GameServer

APP_TITLE = "Aria — Legend Online"
log = logging.getLogger("aria.login")


class _FetchThread(QThread):
    """Fetch server list off the main thread."""
    done = pyqtSignal(list)

    def __init__(self, repo: CachedServerRepository, gamecode: str, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._gamecode = gamecode

    def run(self):
        servers = self._repo.get_servers(self._gamecode)
        self.done.emit(servers)


class LoginDialog(QDialog):
    """Server picker with optional credentials for auto-login."""

    # emits (GameServer, email, password)
    server_chosen = pyqtSignal(object, str, str)

    def __init__(self, launcher=None, parent=None):
        super().__init__(parent)
        self.setObjectName("LoginDialog")
        self.setWindowTitle(APP_TITLE)
        self.setFixedSize(420, 370)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._repo = CachedServerRepository(cache_dir=SERVER_CACHE_DIR)
        self._servers: list[GameServer] = []
        self._last_email = load_last_email()
        self._last_region, self._last_server_id, self._last_password = load_account_session(self._last_email)
        self._loaded_email_key = account_key(self._last_email)
        self._fetch_thread = None
        self._build_ui()
        QTimer.singleShot(100, self._fetch_servers)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(10)

        title = QLabel(f"<h2>{APP_TITLE}</h2>")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignCenter)
        outer.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(24, 0, 24, 0)

        self.cbRegion = QComboBox()
        self.cbRegion.setMinimumWidth(260)
        for code, (display_name, _) in LO_REGIONS.items():
            self.cbRegion.addItem(display_name, code)
        # Restore last region or default to lopl
        restore_region = self._last_region or "lopl"
        idx = self.cbRegion.findData(restore_region)
        if idx >= 0:
            self.cbRegion.setCurrentIndex(idx)
        self.cbRegion.currentIndexChanged.connect(self._on_region_changed)
        form.addRow("Region:", self.cbRegion)

        self.cbServer = QComboBox()
        self.cbServer.setEditable(True)
        self.cbServer.setMinimumWidth(260)
        self.cbServer.setInsertPolicy(QComboBox.NoInsert)
        self.cbServer.lineEdit().setPlaceholderText("Type server ID or pick from list")
        form.addRow("Server:", self.cbServer)

        self.txtEmail = QLineEdit()
        self.txtEmail.setPlaceholderText("(optional — auto-login)")
        if self._last_email:
            self.txtEmail.setText(self._last_email)
        self.txtEmail.editingFinished.connect(self._on_email_changed)
        form.addRow("Email:", self.txtEmail)

        self.txtPassword = QLineEdit()
        self.txtPassword.setEchoMode(QLineEdit.Password)
        self.txtPassword.setPlaceholderText("(optional — auto-login)")
        if self._last_password:
            self.txtPassword.setText(self._last_password)
        form.addRow("Password:", self.txtPassword)

        outer.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(24, 0, 24, 0)
        self.btnPlay = QPushButton("PLAY")
        self.btnPlay.setDefault(True)
        self.btnPlay.clicked.connect(self._on_play)
        btn_row.addStretch()
        btn_row.addWidget(self.btnPlay)
        btn_row.addStretch()
        outer.addLayout(btn_row)

        self.lblStatus = QLabel("")
        self.lblStatus.setObjectName("statusLabel")
        self.lblStatus.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.lblStatus)

        outer.addStretch()

    def _fetch_servers(self):
        gamecode = self.cbRegion.currentData() or "lopl"
        self.lblStatus.setText("Fetching servers...")
        self.lblStatus.setProperty("error", False)
        self.lblStatus.style().unpolish(self.lblStatus)
        self.lblStatus.style().polish(self.lblStatus)
        self.btnPlay.setEnabled(False)

        self._fetch_thread = _FetchThread(self._repo, gamecode, self)
        self._fetch_thread.done.connect(self._on_fetch_done)
        self._fetch_thread.start()

    def _on_fetch_done(self, servers: list):
        self._servers = servers
        self.btnPlay.setEnabled(True)
        self._populate_server_combo()

    def _on_region_changed(self):
        self._fetch_servers()

    def _populate_server_combo(self):
        self.cbServer.clear()
        if not self._servers:
            self.lblStatus.setText("Failed to fetch server list — type a server ID manually")
            self.lblStatus.setProperty("error", True)
            self.lblStatus.style().unpolish(self.lblStatus)
            self.lblStatus.style().polish(self.lblStatus)
            return

        servers = sorted(self._servers, key=lambda s: s.server_id, reverse=True)
        for s in servers:
            prefix = "★ " if s.recommended else ""
            self.cbServer.addItem(f"{prefix}{s.display_name}", s)

        current_region = self.cbRegion.currentData()
        if self._last_server_id and self._last_region == current_region:
            for i in range(self.cbServer.count()):
                srv = self.cbServer.itemData(i)
                if srv and srv.server_id == self._last_server_id:
                    self.cbServer.setCurrentIndex(i)
                    break

        self.lblStatus.setText(f"Loaded {len(servers)} servers")
        self.lblStatus.setProperty("error", False)
        self.lblStatus.style().unpolish(self.lblStatus)
        self.lblStatus.style().polish(self.lblStatus)

    def _on_email_changed(self):
        email = self.txtEmail.text().strip()
        email_key = account_key(email)
        if email_key == self._loaded_email_key:
            return

        self._last_region, self._last_server_id, self._last_password = load_account_session(email)
        self._loaded_email_key = email_key
        self.txtPassword.setText(self._last_password)

        idx = self.cbRegion.findData(self._last_region or "lopl")
        if idx >= 0:
            self.cbRegion.setCurrentIndex(idx)
        else:
            self._fetch_servers()

    def _find_server_by_id(self, sid: int) -> GameServer | None:
        for i in range(self.cbServer.count()):
            srv = self.cbServer.itemData(i)
            if srv and srv.server_id == sid:
                return srv
        return None

    def _on_play(self):
        typed = self.cbServer.currentText().strip()
        idx = self.cbServer.currentIndex()
        server = self.cbServer.itemData(idx) if idx >= 0 else None

        # If user typed a raw server ID, resolve it
        sid = None
        if typed:
            m = re.match(r'^[Ss]?(\d+)$', typed)
            if m:
                sid = int(m.group(1))
                found = self._find_server_by_id(sid)
                if found:
                    server = found
        if typed and not server:
            m = re.search(r'(\d+)', typed)
            if m:
                sid = int(m.group(1))
                server = self._find_server_by_id(sid)

        if not server and sid is not None:
            region = self.cbRegion.currentData() or "lopl"
            server = GameServer(
                server_id=sid,
                name=f"S{sid}",
                fullname=f"Server {sid}",
                region=region
            )

        if not server:
            self.lblStatus.setText("Server not found! Check the ID.")
            self.lblStatus.setProperty("error", True)
            self.lblStatus.style().unpolish(self.lblStatus)
            self.lblStatus.style().polish(self.lblStatus)
            return

        email = self.txtEmail.text().strip()
        password = self.txtPassword.text()
        region = self.cbRegion.currentData() or ""
        save_account_session(region, server.server_id, email, password)

        self.server_chosen.emit(server, email, password)
        self.accept()
