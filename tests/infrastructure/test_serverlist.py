"""Unit tests for CachedServerRepository — mocked HTTP, no network."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aria.infrastructure.serverlist import CachedServerRepository, _parse_servers
from aria.domain.models import GameServer

_SAMPLE = {
    "all": [
        {"server_sid": "1", "server_name": "S1", "fullname": "Server 1",
         "url": "//lobr.example.com/s1", "merger": "0", "recommand": 1},
        {"server_sid": "2", "server_name": "S2", "fullname": "Server 2",
         "url": "//lobr.example.com/s2", "merger": "0", "recommand": 0},
    ]
}


def test_parse_servers_basic():
    servers = _parse_servers(_SAMPLE, "lobr")
    assert len(servers) == 2
    assert servers[0].server_id == 1
    assert servers[0].url == "https://lobr.example.com/s1"
    assert servers[0].recommended is True
    assert servers[1].recommended is False


def test_get_servers_uses_cache_on_failure(tmp_path):
    cache_file = tmp_path / "servers_lobr.json"
    cache_file.write_text(json.dumps(_SAMPLE))

    repo = CachedServerRepository(cache_dir=tmp_path)

    with patch("aria.infrastructure.serverlist._fetch_with_retry", side_effect=Exception("down")):
        servers = repo.get_servers("lobr")

    assert len(servers) == 2
    assert servers[0].region == "lobr"


def test_find_by_id_returns_none_when_missing(tmp_path):
    repo = CachedServerRepository(cache_dir=tmp_path)
    with patch("aria.infrastructure.serverlist._fetch_with_retry", side_effect=Exception("down")):
        result = repo.find_by_id("lobr", 999)
    assert result is None


def test_synthesize_returns_stub():
    from aria.domain.ports import ServerRepository
    repo = CachedServerRepository(cache_dir=Path("/tmp"))
    stub = repo.synthesize("lobr", 42)
    assert stub.server_id == 42
    assert stub.region == "lobr"
    assert "42" in stub.name
