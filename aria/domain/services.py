"""LauncherService — facade over auth + server resolution."""

from __future__ import annotations

import logging

from .models import GameServer
from .ports import CredentialStore, ServerRepository

log = logging.getLogger("aria.domain")


class LauncherService:
    """
    Orchestrates login and server selection.
    Injected with infrastructure implementations — no I/O in this class.
    """

    def __init__(
        self,
        server_repo: ServerRepository,
        credential_store: CredentialStore,
    ) -> None:
        self._servers = server_repo
        self._creds = credential_store

    # ------------------------------------------------------------------
    # Credential management
    # ------------------------------------------------------------------

    def save_credentials(self, email: str, password: str) -> None:
        self._creds.save(email, password)

    def load_password(self, email: str) -> str | None:
        return self._creds.load(email)

    def delete_credentials(self, email: str) -> None:
        self._creds.delete(email)

    # ------------------------------------------------------------------
    # Server resolution
    # ------------------------------------------------------------------

    def get_servers(self, region: str) -> list[GameServer]:
        return self._servers.get_servers(region)

    def resolve_server(self, region: str, server_id: int) -> GameServer:
        """
        Return a GameServer by ID.
        Falls back to a synthesized stub if the API is unavailable.
        """
        server = self._servers.find_by_id(region, server_id)
        if server is None:
            log.warning(
                "Server %d not found in API response — synthesizing stub", server_id
            )
            server = self._servers.synthesize(region, server_id)
        return server

    def build_server_url(self, server: GameServer, regions: dict) -> str:
        """Build the serverlist URL for a given server."""
        from .models import GameServer as _GS  # avoid circular at module level
        region_prefix = server.region or "lopl"
        if region_prefix in regions:
            region_prefix = regions[region_prefix][1]
        return f"https://{region_prefix}.creaction-network.com/serverlist/s{server.server_id}?pay_later=1"
