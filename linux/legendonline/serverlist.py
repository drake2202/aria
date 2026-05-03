"""
Server list model — fetches Legend Online server lists from the OAS Games API
across all regional game codes (lopl, lobr, loes, lotr, lorpt, lode, loar, etc.).

API endpoint: https://odp3.oasgames.com/api/game/serverlist?gamecode={code}
Response key:  {"all": [ {server_sid, server_name, fullname, url, merger, recommand, …}, … ]}
"""

import json
import logging
from dataclasses import dataclass, field

import requests

from .config import SERVER_LIST_INI, CONFIG_DIR, LO_REGIONS, OAS_API_URL

log = logging.getLogger("serverlist")


@dataclass
class GameServer:
    server_id: int = 0
    name: str = ""
    fullname: str = ""
    url: str = ""
    merger: int = 0          # 0 = standalone merge target, else merged-into sid
    recommended: bool = False
    region: str = ""         # gamecode e.g. "lopl", "lobr"

    @property
    def display_name(self) -> str:
        return self.fullname or f"S{self.server_id}:{self.name}"


@dataclass
class ServerListModel:
    servers: list[GameServer] = field(default_factory=list)

    def fetch(self, gamecode: str = "lopl"):
        """Fetch the server list for a single region from OAS API."""
        self.servers.clear()
        self._fetch_region(gamecode)

    def fetch_all(self):
        """Fetch server lists from ALL Legend Online regions."""
        self.servers.clear()
        for code in LO_REGIONS:
            self._fetch_region(code)
        log.info("Total servers across all regions: %d", len(self.servers))

    def _fetch_region(self, gamecode: str):
        """Fetch servers for a specific gamecode and append to self.servers."""
        url = OAS_API_URL.format(gamecode=gamecode)
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("all", data) if isinstance(data, dict) else data
            if not isinstance(entries, list):
                log.warning("Unexpected API response for %s", gamecode)
                return
            count = 0
            for entry in entries:
                raw_url = entry.get("url", "")
                if raw_url.startswith("//"):
                    raw_url = "https:" + raw_url
                merger_val = entry.get("merger", 0)
                if isinstance(merger_val, str):
                    merger_val = int(merger_val) if merger_val.isdigit() else 0
                self.servers.append(GameServer(
                    server_id=int(entry.get("server_sid", 0)),
                    name=entry.get("server_name", ""),
                    fullname=entry.get("fullname", ""),
                    url=raw_url,
                    merger=merger_val,
                    recommended=bool(entry.get("recommand", 0)),
                    region=gamecode,
                ))
                count += 1
            log.info("Loaded %d servers for %s", count, gamecode)
        except Exception as e:
            log.error("Server list fetch failed for %s: %s", gamecode, e)

    def active_servers(self, region: str | None = None) -> list[GameServer]:
        """Return only the merge-target (playable) servers, newest first.
        Optionally filter by region gamecode."""
        pool = self.servers
        if region:
            pool = [s for s in pool if s.region == region]
        targets = {s.merger for s in pool if s.merger != 0}
        active = [s for s in pool if s.merger == 0 or s.server_id in targets]
        seen = set()
        result = []
        for s in active:
            key = (s.region, s.server_id)
            if key not in seen:
                seen.add(key)
                result.append(s)
        return result

    def _load_local_ini(self):
        if not SERVER_LIST_INI.exists():
            return
        try:
            text = SERVER_LIST_INI.read_text()
            for line in text.splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("[") and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    self.servers.append(GameServer(
                        server_id=0,
                        name=key.strip(),
                        url=val.strip(),
                    ))
        except Exception as e:
            log.warning("Failed to read local server list: %s", e)

    def save_ini(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        lines = ["[Servers]"]
        for s in self.servers:
            if s.url:
                lines.append(f"{s.fullname}={s.url}")
        SERVER_LIST_INI.write_text("\n".join(lines))
