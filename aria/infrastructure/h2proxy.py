"""
H2Proxy — Linux-native reimplementation of the Brov H2Proxy helper.

Provides:
  - HTTP reverse proxy on 127.0.0.1:8125
  - /revproxy/{host}/{path} — cached reverse proxy
  - /addRevProxyMapping/ — register host mapping
  - /getResServer/{id} — resolve resource server
  - /known-hosts/tsv/ — return known host latency table
  - /polipo/ — proxy status page
  - /crossdomain.xml — Flash cross-domain policy
  - WebSocket-to-TCP bridge on a secondary port
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path

from aiohttp import web, ClientSession, ClientTimeout

from .config import (
    PROXY_HOST,
    PROXY_PORT,
    KNOWN_RES_SERVERS,
    CACHE_DIR,
    CROSS_DOMAIN_POLICY_XML,
    CROSS_DOMAIN_SOCKET_POLICY_XML,
    REDIRECT_CACHE,
)

log = logging.getLogger("h2proxy")


class H2Proxy:
    """Async HTTP helper service replicating H2Proxy.exe behavior."""

    def __init__(self, host: str = PROXY_HOST, port: int = PROXY_PORT):
        self.host = host
        self.port = port
        self._mappings: dict[str, str] = dict(KNOWN_RES_SERVERS)
        self._cache_dir = CACHE_DIR / "h2proxy"
        self._redirect_cache: dict[str, str] = {}
        self._host_stats: dict[str, dict] = {}
        self._session: ClientSession | None = None
        self._runner: web.AppRunner | None = None
        # In-memory LRU: keeps hot assets (SWFs, images) in RAM
        self._mem_cache: OrderedDict[str, tuple[bytes, str]] = OrderedDict()
        self._mem_cache_max = 128 * 1024 * 1024  # 128 MB budget
        self._mem_cache_size = 0

    # -- lifecycle --

    async def start(self):
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_redirect_cache()
        self._session = ClientSession(timeout=ClientTimeout(total=30))

        app = web.Application()
        app.router.add_route("*", "/revproxy/{tail:.*}", self._handle_revproxy)
        app.router.add_post("/addRevProxyMapping/", self._handle_add_mapping)
        app.router.add_get("/getResServer/{server_id}", self._handle_get_res_server)
        app.router.add_get("/known-hosts/tsv/", self._handle_known_hosts)
        app.router.add_get("/polipo/", self._handle_polipo)
        app.router.add_get("/crossdomain.xml", self._handle_crossdomain)
        # Flash socket policy
        app.router.add_get("/", self._handle_root)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        log.info("H2Proxy listening on %s:%d", self.host, self.port)

    async def stop(self):
        self._save_redirect_cache()
        if self._session:
            await self._session.close()
        if self._runner:
            await self._runner.cleanup()
        log.info("H2Proxy stopped")

    # -- handlers --

    async def _handle_revproxy(self, request: web.Request) -> web.StreamResponse:
        tail = request.match_info["tail"]
        if not tail:
            return web.Response(status=400, text="Missing proxy target")

        parts = tail.split("/", 1)
        host = parts[0]
        path = "/" + parts[1] if len(parts) > 1 else "/"

        mapped_host = self._mappings.get(host, host)
        url = f"https://{mapped_host}{path}"
        if request.query_string:
            url += "?" + request.query_string

        cache_key = hashlib.sha256(url.encode()).hexdigest()

        # 1. In-memory LRU hit (fastest)
        if cache_key in self._mem_cache:
            body, content_type = self._mem_cache[cache_key]
            self._mem_cache.move_to_end(cache_key)
            self._record_stat(mapped_host, cached=True)
            return web.Response(body=body, headers={
                "Content-Type": content_type,
                "X-H2Proxy-Cache": "MEM",
                "Cache-Control": "public, max-age=86400, immutable",
            })

        # 2. Disk cache hit
        cache_file = self._cache_dir / cache_key
        if cache_file.exists():
            try:
                meta = json.loads((self._cache_dir / (cache_key + ".meta")).read_text())
                body = cache_file.read_bytes()
                content_type = meta.get("content_type", "application/octet-stream")
                self._mem_cache_put(cache_key, body, content_type)
                self._record_stat(mapped_host, cached=True)
                return web.Response(body=body, headers={
                    "Content-Type": content_type,
                    "X-H2Proxy-Cache": "DISK",
                    "Cache-Control": "public, max-age=86400, immutable",
                })
            except Exception:
                pass

        # 3. Fetch from upstream
        t0 = time.monotonic()
        try:
            async with self._session.get(url) as upstream:
                body = await upstream.read()
                content_type = upstream.headers.get("Content-Type", "application/octet-stream")
                lag = int((time.monotonic() - t0) * 1000)
                self._record_stat(mapped_host, cached=False, lag=lag, size=len(body))

                if upstream.status == 200:
                    cache_file.write_bytes(body)
                    (self._cache_dir / (cache_key + ".meta")).write_text(
                        json.dumps({"content_type": content_type, "url": url, "ts": time.time()})
                    )
                    self._mem_cache_put(cache_key, body, content_type)

                return web.Response(
                    status=upstream.status,
                    body=body,
                    headers={
                        "Content-Type": content_type,
                        "X-H2Proxy-Cache": "MISS",
                        "Cache-Control": "public, max-age=3600" if upstream.status == 200 else "no-cache",
                    },
                )
        except Exception as e:
            log.warning("revproxy fetch failed for %s: %s", url, e)
            return web.Response(status=502, text=str(e))

    async def _handle_add_mapping(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            name = data.get("name", "")
            target = data.get("target", "")
            if name and target:
                self._mappings[name] = target
                log.info("Added proxy mapping: %s -> %s", name, target)
                return web.Response(text="OK")
            return web.Response(status=400, text="Missing name or target")
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

    async def _handle_get_res_server(self, request: web.Request) -> web.Response:
        server_id = request.match_info["server_id"]
        host = self._mappings.get(server_id, "")
        if host:
            return web.Response(text=host)
        return web.Response(status=404, text="Unknown server")

    async def _handle_known_hosts(self, _request: web.Request) -> web.Response:
        lines = ["Host\tLag (ms)\tTotal req\tCached req\tIn-flight\tSpeed"]
        for host, stats in self._host_stats.items():
            lines.append(
                f"{host}\t{stats.get('lag', 0)}\t{stats.get('total', 0)}\t"
                f"{stats.get('cached', 0)}\t0\t{stats.get('speed', '-')}"
            )
        return web.Response(text="\n".join(lines), content_type="text/tab-separated-values")

    async def _handle_polipo(self, _request: web.Request) -> web.Response:
        html = (
            "<html><head><title>H2Proxy Status</title></head><body>"
            "<h1>H2Proxy Status</h1>"
            "<p>Proxy enabled</p>"
            f"<p>Mappings: {len(self._mappings)}</p>"
            f"<p>Cache dir: {self._cache_dir}</p>"
            "<table border='1'><tr><th>Host</th><th>Lag (ms)</th>"
            "<th>Total req</th><th>Cached req</th></tr>"
        )
        for host, stats in self._host_stats.items():
            html += (
                f"<tr><td>{host}</td><td>{stats.get('lag', 0)}</td>"
                f"<td>{stats.get('total', 0)}</td><td>{stats.get('cached', 0)}</td></tr>"
            )
        html += "</table></body></html>"
        return web.Response(text=html, content_type="text/html")

    async def _handle_crossdomain(self, _request: web.Request) -> web.Response:
        return web.Response(text=CROSS_DOMAIN_POLICY_XML, content_type="text/xml")

    async def _handle_root(self, _request: web.Request) -> web.Response:
        return web.Response(text=CROSS_DOMAIN_SOCKET_POLICY_XML, content_type="text/xml")

    # -- helpers --

    def _mem_cache_put(self, key: str, body: bytes, content_type: str):
        """Store item in memory LRU, evicting old entries if over budget."""
        size = len(body)
        if size > self._mem_cache_max // 4:
            return  # skip items larger than 25% of budget
        # Evict LRU entries until there's room
        while self._mem_cache_size + size > self._mem_cache_max and self._mem_cache:
            _, (old_body, _) = self._mem_cache.popitem(last=False)
            self._mem_cache_size -= len(old_body)
        self._mem_cache[key] = (body, content_type)
        self._mem_cache_size += size

    def _record_stat(self, host: str, cached: bool, lag: int = 0, size: int = 0):
        if host not in self._host_stats:
            self._host_stats[host] = {"total": 0, "cached": 0, "lag": 0, "speed": "-"}
        s = self._host_stats[host]
        s["total"] += 1
        if cached:
            s["cached"] += 1
        if lag:
            s["lag"] = lag
        if size and lag:
            s["speed"] = f"{size / (lag / 1000) / 1024:.0f} KB/s"

    def _load_redirect_cache(self):
        if REDIRECT_CACHE.exists():
            try:
                self._redirect_cache = json.loads(REDIRECT_CACHE.read_text())
            except Exception:
                self._redirect_cache = {}

    def _save_redirect_cache(self):
        REDIRECT_CACHE.parent.mkdir(parents=True, exist_ok=True)
        REDIRECT_CACHE.write_text(json.dumps(self._redirect_cache))
