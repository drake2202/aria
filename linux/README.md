# Aria — Linux Native Client

Aria is a Linux-native client for Legend Online using `PyQt5` + `QtWebEngine`
with PepperFlash PPAPI support.

## System Requirements

- Python 3.11+
- PyQt5 + PyQtWebEngine
- aiohttp
- requests

### Arch Linux

```bash
sudo pacman -S python python-pip
```

### Debian/Ubuntu

```bash
sudo apt install python3 python3-pip
```

### pip (any distro)

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
cd /home/zero/dev/brov/linux
chmod +x run.sh
./run.sh
```

Or run as a Python module:

```bash
cd /home/zero/dev/brov/linux
.venv/bin/python3 -m legendonline
```

## Build Commands (Makefile)

```bash
cd /home/zero/dev/brov/linux
make deps
make build
```

Useful targets:

- `make run` - run from source
- `make clean` - remove build artifacts
- `make aur-srcinfo` - regenerate `aur/aria-git/.SRCINFO`

## Desktop Integration

```bash
cd /home/zero/dev/brov/linux
./install-app.sh
```

The installer prefers the built binary at `dist/aria`. If that file does not
exist yet, it installs a small wrapper in `~/.local/bin/aria` that launches the
repo checkout via `run.sh`.

This makes Aria show up in launcher menus that read XDG desktop entries,
including Rofi (`drun`) and XFCE.

## What It Does

1. **Single-instance lock** — only one launcher process at a time
2. **H2Proxy helper** — local HTTP reverse proxy on `127.0.0.1:8125`
   - `/revproxy/*` — cached reverse proxy with host mapping
   - `/addRevProxyMapping/` — dynamic host registration
   - `/getResServer/{id}` — resource server resolution
   - `/known-hosts/tsv/` — host latency table
   - `/polipo/` — status dashboard
   - `/crossdomain.xml` — Flash cross-domain policy
3. **Server list** — fetches regional server lists via OAS API
4. **Flash game embedding** — QtWebEngine with PepperFlash (`libpepflashplayer.so`)
5. **Map viewer** — displays bundled Basic/Advanced/Expert maps
6. **Aria UI** — rounded black/white theme with streamlined in-game view

## Project Structure

```
linux/
├── run.sh                      # Launch script
├── Aria.desktop                # Desktop entry
├── README.md                   # This file
└── legendonline/
    ├── __init__.py             # Package metadata
    ├── __main__.py             # Entry point / orchestration
    ├── config.py               # Hardcoded config from RE
    ├── h2proxy.py              # H2Proxy native clone
    ├── serverlist.py           # Server list model
    ├── gameview.py             # Flash/WebEngine game widget
   └── mapdialog.py            # Map viewer dialog
```

## Data Locations

- Config: `~/.config/Aria/`
- Cache: `~/.cache/Aria/`
- Data: `~/.local/share/Aria/`

## Flash Plugin

Place `libpepflashplayer.so` in `brov/flash/` (already present).
The launcher auto-detects it and configures Chromium PPAPI flags.

## Notes

- Aria stores last selected server and optional login credentials locally.
- H2Proxy uses both disk cache and in-memory LRU cache for faster asset loads.
