# StorCloud

StorCloud is a **local-first gaming platform**. The server organizes the library and sessions, but games should render on the player's hardware whenever possible.

## v0.5 Local First

Current execution order:

1. **Browser WASM / WebGPU** — real browser ports run directly on the player's CPU/GPU.
2. **Retro Library** — one unified Nostalgist.js + RetroArch WASM player; emulator cores are hidden from the user.
3. **PC Local** — the StorCloud Local Agent launches allowlisted Windows/Linux games on the player's machine.
4. **Remote Streaming** — fallback only when no local execution path is viable.

An arbitrary Windows `.exe` is not automatically convertible to WebAssembly. Native PC games use a real browser port when available, otherwise the Local Agent or, as a last resort, remote streaming.

## What is included now

- FastAPI control-plane API
- Docker Compose deployment
- web launcher
- Doom / FreeDoom browser-WASM package bootstrap
- unified Retro Library
- automatic retro platform/core mapping
- save-state controls in the unified Retro player
- PC Local status page
- Rust StorCloud Local Agent alpha
- allowlisted local game launching
- Windows/Linux Local Agent CI builds
- automatic cleanup of the old separate-emulator runtime

## Quick update

On the StorCloud Ubuntu VM:

```bash
cd /opt/storcloud
git pull
bash update.sh
```

Open:

- Launcher: `http://SERVER_IP:8080`
- Retro Library: `http://SERVER_IP:8080/retro/`
- PC Local: `http://SERVER_IP:8080/pc/`
- API: `http://SERVER_IP:8000`
- API docs: `http://SERVER_IP:8000/docs`

## Repository layout

```text
backend/api/                  FastAPI control plane
frontend/                     launcher and browser experiences
frontend/retro/               one unified Retro player
frontend/pc/                  Local Agent/device status UI
local-agent/                  native Rust companion for PC games
runtime/                      generated/downloaded payloads; not committed
scripts/bootstrap-games.sh    browser game package installer
scripts/cleanup-legacy-retro.sh
scripts/build-local-agent.sh
update.sh                     server update entrypoint
docs/                         architecture and operations documentation
```

## Retro

The user does **not** choose an emulator. StorCloud selects the core internally based on the platform/file type.

Initial mapping includes NES, SNES, GB/GBC, GBA, Mega Drive, Master System, Game Gear, Arcade/Neo Geo, with N64 and PS1 marked experimental.

ROMs, BIOS files and proprietary commercial game assets are not bundled in this repository.

## PC Local Agent

The agent binds only to `127.0.0.1:47831`. It exposes health/capability endpoints and authenticated allowlisted game launching. It does not accept arbitrary shell commands or executable paths from a website.

See:

- `local-agent/README.md`
- `docs/LOCAL-PC-RUNTIME.md`

## Documentation

- `docs/ARCHITECTURE.md` — complete local-first runtime model
- `docs/LOCAL-PC-RUNTIME.md` — PC/native execution design and security model
- `docs/DEPLOYMENT.md` — Ubuntu deployment, cleanup and verification

## Legacy cleanup

Older development builds installed separate mGBA, FBNeo, N64, PPSSPP, SNES9x and BlastEm runtime directories. They are no longer used. `bash update.sh` now removes these legacy payloads automatically while preserving current browser-game packages such as Doom/FreeDoom.
