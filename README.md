# Aria — Legend Online Launcher

Native macOS and Linux launcher for **Legend Online** (Flash game) using PyQt5 + PepperFlash PPAPI.

Supported platforms: **x86_64** and **ARM64** on any major Linux distribution, plus macOS.

---

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.10+ |
| PyQt5 | 5.15+ |
| PyQtWebEngine | 5.15+ |
| aiohttp | 3.x |
| requests | 2.28+ |
| keyring | 24+ *(optional — for secure credential storage)* |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/drake2202/aria.git
cd aria
```

### 2. Install system dependencies and Python packages

The quickest way is the included distro-aware installer, which works on **any major Linux distribution** and both **x86_64 and ARM64**:

```bash
bash scripts/install.sh
```

The script auto-detects your distribution and calls the right package manager:

| Distribution | Package manager |
|---|---|
| Ubuntu / Debian / Mint / Pop!_OS | `apt` |
| Fedora | `dnf` |
| RHEL / CentOS / AlmaLinux / Rocky | `dnf` or `yum` |
| Arch / Manjaro / EndeavourOS | `pacman` |
| openSUSE Leap / Tumbleweed | `zypper` |
| Alpine Linux | `apk` |

After the script finishes, skip to [Running the app](#running-the-app).

#### Manual setup (optional)

If you prefer to manage dependencies yourself:

```bash
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
pip install -e .
```

> **Windows** is not yet supported. The launcher targets macOS and Linux only.

---

## Running the app

```bash
# From the repo root, with your venv active:
python3 -m aria
```

Or if you installed with `pip install -e .`:

```bash
aria
```

---

## ARM64 Support

Aria runs natively on **ARM64 (aarch64)** Linux machines (Raspberry Pi 4/5, Apple Silicon Linux VMs, AWS Graviton, etc.).

> **Note:** PepperFlash is not available for ARM64 from Adobe. On ARM64 the launcher will start but Flash-dependent content may not render. All non-Flash features (server list, account management, proxy) work normally.

AppImages for both **x86_64** and **aarch64** are published for every release.

---

## Flash Plugin

The PepperFlash plugins are bundled in the `flash/` directory:

```
flash/
├── linux/
│   ├── x64/libpepflashplayer.so    ← Linux x86_64
│   └── ia32/libpepflashplayer.so   ← Linux 32-bit x86
└── mac/
    └── x64/PepperFlashPlayer.plugin  ← macOS
```

> **ARM64 note:** Adobe never released a PepperFlash plugin for Linux ARM64. The `arm64` sub-directory is not included in the bundle. On ARM64 machines the launcher starts normally but Flash-dependent game content will not render (same as the message shown in the [ARM64 Support](#arm64-support) section above).

The launcher auto-detects your OS and architecture at startup — no configuration needed.

---

## How it works

```
startup
  │
  ├── FlashAdapter.configure()        ← injects PPAPI flags into sys.argv BEFORE Qt starts
  ├── H2Proxy starts (port 8125)      ← reverse proxy for cross-domain Flash assets
  ├── LoginDialog                     ← pick region + server, optional auto-login
  │
  └── GameWindow
        ├── loads serverlist page     ← keeps session/auth context
        ├── detects game.jsp iframe   ← JS injection: position:fixed, 100% viewport
        └── 800ms settle delay        ← Flash initializes, then menubar hides
```

### Why we stay on the serverlist page

The game's `shenqu.js` calls `parent.*` functions for authentication — navigating the main frame away from the serverlist page breaks the auth bridge. Instead, we detect the `game.jsp` iframe and make it fullscreen using CSS (`position:fixed; z-index:2147483647`). Clicks pass naturally to Flash through the iframe.

---

## Project Structure

```
aria/
├── __main__.py              ← entry point + DI wiring
├── domain/
│   ├── models.py            ← GameServer, Account, AuthToken (pure Python)
│   ├── ports.py             ← ServerRepository, CredentialStore (ABCs)
│   └── services.py          ← LauncherService facade
├── infrastructure/
│   ├── config.py            ← platform paths, constants
│   ├── serverlist.py        ← OAS API fetch with retry + disk cache
│   ├── credentials.py       ← keyring-backed secure credential store
│   ├── account_store.py     ← JSON account persistence
│   ├── h2proxy.py           ← HTTP reverse proxy (aiohttp)
│   └── flash/
│       ├── base.py          ← FlashAdapter ABC
│       ├── macos.py         ← macOS PPAPI resolver
│       └── linux.py         ← Linux PPAPI resolver
└── presentation/
    ├── gameview.py          ← QtWebEngine + Flash integration
    ├── gamewindow.py        ← main game window (menubar, account switch)
    ├── login_dialog.py      ← server picker dialog
    └── stylesheet.py        ← Qt stylesheets
```

---

## Credentials & Security

Passwords are stored in the **OS keychain** via the `keyring` library:
- **macOS**: Keychain
- **Linux**: libsecret / GNOME Keyring / KWallet

If `keyring` is unavailable, credentials are kept **in memory only** for the session — nothing is written to disk in plaintext.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (no display required — domain + infrastructure only)
pytest tests/ -q

# Lint
ruff check aria/ tests/

# Type-check
mypy aria/domain/ aria/infrastructure/
```

---

## Supported Regions

| Code | Server |
|---|---|
| `lopl` | Legend Online Polska |
| `lobr` | Legend Online Brasileiro |
| `loes` | Legend Online Español |
| `lotr` | Legend Online Türkçe |
| `lorpt` | Legend Online Português |
| `lode` | Legend Online Deutsch |
| `loar` | Legend Online العربية |
| `lonl` | Legend Online Nederlands |
| `losv` | Legend Online Svenska |
| `loel` | Legend Online Ελληνικά |
| `lortr` | Legend Online Classic Türkçe |
| `loru` | Legend Online Русский |

---

## Troubleshooting

### Black screen / Flash not loading
- Check that `flash/` plugin exists for your platform: `python3 -c "from aria.infrastructure.flash.macos import MacOSFlashAdapter; print(MacOSFlashAdapter().plugin_path())"`
- Use **Tools → Test Flash** in the game window menubar

### Can't click in the game
- This is a known issue if something intercepts mouse events. The launcher uses `Qt.NoContextMenu` to give Flash full control of right-click. If left-click is broken, check your Qt version (`PyQt5 5.15.x` required).

### Server list fails to load
- The OAS API may be down — you can still type a server ID directly (e.g. `3229` or `s3229`) in the server field.
- The launcher caches the last successful server list in `~/.cache/Aria/servers/` and falls back to it automatically.

### macOS: "damaged app" / Gatekeeper
```bash
xattr -cr /path/to/Aria.app
```
