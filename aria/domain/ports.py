"""Domain ports — abstract interfaces for infrastructure adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import GameServer


class ServerRepository(ABC):
    """Fetch and query game servers."""

    @abstractmethod
    def get_servers(self, region: str) -> list[GameServer]:
        """Return all servers for the given region gamecode."""

    @abstractmethod
    def find_by_id(self, region: str, server_id: int) -> GameServer | None:
        """Return a specific server, or None if not found."""

    def synthesize(self, region: str, server_id: int) -> GameServer:
        """Synthesize a minimal GameServer when API is unavailable."""
        return GameServer(
            server_id=server_id,
            name=f"S{server_id}",
            fullname=f"Server {server_id}",
            region=region,
        )


class CredentialStore(ABC):
    """Secure credential storage — never plaintext on disk."""

    @abstractmethod
    def save(self, email: str, password: str) -> None:
        """Persist credentials securely."""

    @abstractmethod
    def load(self, email: str) -> str | None:
        """Return the stored password, or None."""

    @abstractmethod
    def delete(self, email: str) -> None:
        """Remove stored credentials."""
