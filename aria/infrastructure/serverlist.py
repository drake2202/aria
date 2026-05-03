"""Infrastructure: OAS Games server list with retry + disk cache."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from aria.domain.models import GameServer
from aria.domain.ports import ServerRepository

log = logging.getLogger("aria.serverlist")

_OAS_API = "https://odp3.oasgames.com/api/game/serverlist?gamecode={gamecode}"
_TIMEOUT = 15
_MAX_RETRIES = 3


def _fetch_with_retry(url: str) -> requests.Response:
    for attempt in range(_MAX_RETRIES):
        try:
            return requests.get(url, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            if attempt == _MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt  # 1s, 2s
            log.warning("Fetch failed (attempt %d/%d), retrying in %ds: %s", attempt + 1, _MAX_RETRIES, wait, exc)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def _parse_servers(data: dict | list, region: str) -> list[GameServer]:
    entries = data.get("all", data) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return []
    servers = []
    for entry in entries:
        raw_url = entry.get("url", "")
        if raw_url.startswith("//"):
            raw_url = "https:" + raw_url
        merger = entry.get("merger", 0)
        if isinstance(merger, str):
            merger = int(merger) if merger.isdigit() else 0
        servers.append(GameServer(
            server_id=int(entry.get("server_sid", 0)),
            name=entry.get("server_name", ""),
            fullname=entry.get("fullname", ""),
            url=raw_url,
            merger=merger,
            recommended=bool(entry.get("recommand", 0)),
            region=region,
        ))
    return servers


class CachedServerRepository(ServerRepository):
    """
    Fetches servers from OAS API with exponential-backoff retry.
    Caches results to disk — if the API is unreachable, serves the last
    known good list so the launcher can still start offline.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, list[GameServer]] = {}

    def _cache_path(self, region: str) -> Path:
        return self._cache_dir / f"servers_{region}.json"

    def _load_cache(self, region: str) -> list[GameServer]:
        p = self._cache_path(region)
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text())
            return _parse_servers(data, region)
        except Exception as e:
            log.warning("Cache read failed for %s: %s", region, e)
            return []

    def _save_cache(self, region: str, raw: dict | list) -> None:
        try:
            self._cache_path(region).write_text(json.dumps(raw))
        except Exception as e:
            log.warning("Cache write failed for %s: %s", region, e)

    def get_servers(self, region: str) -> list[GameServer]:
        if region in self._memory:
            return self._memory[region]

        url = _OAS_API.format(gamecode=region)
        try:
            resp = _fetch_with_retry(url)
            resp.raise_for_status()
            raw = resp.json()
            servers = _parse_servers(raw, region)
            self._save_cache(region, raw)
            log.info("Loaded %d servers for %s", len(servers), region)
        except Exception as e:
            log.error("API fetch failed for %s: %s — using cache", region, e)
            servers = self._load_cache(region)
            if not servers:
                log.warning("No cached servers for %s", region)

        self._memory[region] = servers
        return servers

    def find_by_id(self, region: str, server_id: int) -> GameServer | None:
        for s in self.get_servers(region):
            if s.server_id == server_id:
                return s
        return None
