"""Unit tests for domain models — zero Qt, zero I/O."""
import pytest
from aria.domain.models import GameServer, Account, AuthToken


def test_game_server_display_name_uses_fullname():
    s = GameServer(server_id=1, name="S1", fullname="Server One", region="lopl")
    assert s.display_name == "Server One"


def test_game_server_display_name_fallback():
    s = GameServer(server_id=42, name="sv42", fullname="", region="lobr")
    assert s.display_name == "S42:sv42"


def test_game_server_is_frozen():
    s = GameServer(server_id=1, name="S1", fullname="Server 1", region="lopl")
    with pytest.raises(Exception):
        s.server_id = 2  # type: ignore[misc]


def test_auth_token_fields():
    t = AuthToken(user_id="abc", key="xyz", site="lopl")
    assert t.user_id == "abc"
    assert t.key == "xyz"
    assert t.site == "lopl"
