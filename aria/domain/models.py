"""Domain models — pure Python, zero Qt, zero I/O."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GameServer:
    """A Legend Online game server."""
    server_id: int
    name: str
    fullname: str
    region: str
    url: str = ""
    merger: int = 0
    recommended: bool = False

    @property
    def display_name(self) -> str:
        return self.fullname or f"S{self.server_id}:{self.name}"


@dataclass(frozen=True)
class Account:
    """A stored user account."""
    email: str
    region: str = ""
    server_id: int = 0


@dataclass(frozen=True)
class AuthToken:
    """Session tokens embedded in the game.jsp URL."""
    user_id: str
    key: str
    site: str
