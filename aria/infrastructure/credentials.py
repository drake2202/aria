"""Infrastructure: keyring-backed credential store."""

from __future__ import annotations

import logging

from aria.domain.ports import CredentialStore

log = logging.getLogger("aria.credentials")

_SERVICE = "aria-launcher"


class SystemCredentialStore(CredentialStore):
    """
    Stores passwords in the OS secure keychain.
    - macOS: Keychain
    - Linux: libsecret / GNOME Keyring / KWallet
    - Windows: Windows Credential Locker

    Requires `keyring` package.
    Falls back to in-memory store if keyring is unavailable.
    """

    def __init__(self) -> None:
        try:
            import keyring as _kr
            self._kr = _kr
            log.info("Credential store: OS keychain (%s)", _kr.get_keyring().__class__.__name__)
        except ImportError:
            log.warning("keyring not installed — credentials stored in memory only")
            self._kr = None
        self._memory: dict[str, str] = {}

    def save(self, email: str, password: str) -> None:
        if not email:
            return
        self._memory[email] = password
        if self._kr:
            try:
                self._kr.set_password(_SERVICE, email, password)
            except Exception as e:
                log.warning("Keychain save failed: %s", e)

    def load(self, email: str) -> str | None:
        if not email:
            return None
        if email in self._memory:
            return self._memory[email]
        if self._kr:
            try:
                return self._kr.get_password(_SERVICE, email)
            except Exception as e:
                log.warning("Keychain load failed: %s", e)
        return None

    def delete(self, email: str) -> None:
        self._memory.pop(email, None)
        if self._kr:
            try:
                self._kr.delete_password(_SERVICE, email)
            except Exception as e:
                log.warning("Keychain delete failed: %s", e)
