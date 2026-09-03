# StorCloud

StorCloud is a **local-first multi-user gaming platform**. The server organizes accounts, devices, saves, libraries and launch authorization, while games should render on the player's own hardware whenever possible.

## v0.6 Multiuser Control Plane

Execution order:

1. **Browser WASM / WebGPU** — real browser ports run directly on the player's CPU/GPU.
2. **Retro Library** — one unified Nostalgist.js + RetroArch WASM player; emulator cores remain an implementation detail.
3. **PC Local** — StorCloud Local Agent launches allowlisted Windows/Linux games on the player's machine.
4. **Remote Streaming** — fallback only when no viable local execution path exists.

An arbitrary Windows `.exe` is not generically converted to WebAssembly. Native games use a real browser port when available, otherwise the Local Agent or remote streaming fallback.

## Included now

- FastAPI control-plane API
- PostgreSQL persistent database
- multi-user registration/login
- first-admin setup token
- HttpOnly server sessions
- user/device model
- 10-minute Local Agent pairing tickets
- per-device credentials stored only by the Local Agent
- 45-second one-time PC launch tickets
- Local Agent heartbeat/device presence
- cloud save-state storage per user/game/slot
- unified Retro Library with cloud-save fallback to local files
- Doom / FreeDoom browser-WASM package bootstrap
- PC Local launch UI
- Rust Local Agent v0.2
- Windows/Linux Local Agent CI builds
- API/PostgreSQL integration smoke test
- automatic cleanup of old separate-emulator payloads

## Update the Ubuntu server

```bash
cd /opt/storcloud
git pull
bash update.sh
```

`update.sh` creates `.env` on first run with a random PostgreSQL password and first-admin setup token, cleans legacy retro payloads, prepares browser games, rebuilds containers and checks API/database health.

Open:

- Launcher: `http://SERVER_IP:8080`
- Account: `http://SERVER_IP:8080/account/`
- Retro Library: `http://SERVER_IP:8080/retro/`
- PC Local: `http://SERVER_IP:8080/pc/`
- API: `http://SERVER_IP:8000`
- API docs: `http://SERVER_IP:8000/docs`

## First administrator

After the first v0.6 update, read the generated setup token on the VM:

```bash
grep '^STORCLOUD_SETUP_TOKEN=' /opt/storcloud/.env
```

Open `/account/`, create the first account and provide that token. Only the first account can become admin this way.

## Persistent data

- PostgreSQL: Docker volume `storcloud-postgres`
- save-state files: `/opt/storcloud/storage/saves`
- browser game payloads: `/opt/storcloud/runtime/games`
- server secrets: `/opt/storcloud/.env` (ignored by Git)

Do not delete the PostgreSQL volume or `storage/` when updating.

## Repository layout

```text
backend/api/                  FastAPI multi-user control plane
frontend/                     web launcher
frontend/account/             login, users, device pairing and save dashboard
frontend/retro/               unified Retro player + cloud saves
frontend/pc/                  Local Agent pairing/launch experience
local-agent/                  native Rust companion for PC games
runtime/                      generated/downloaded browser payloads; not committed
storage/                      persistent save files; not committed
scripts/bootstrap-env.sh      generates persistent server secrets
scripts/bootstrap-games.sh    browser game package installer
scripts/cleanup-legacy-retro.sh
update.sh                     Ubuntu update/deploy entrypoint
docs/                         architecture and operations documentation
```

## Retro

The user chooses a game, not an emulator. StorCloud maps the platform to the appropriate RetroArch WebAssembly core internally.

Initial mapping includes NES, SNES, GB/GBC, GBA, Mega Drive, Master System, Game Gear and Arcade/Neo Geo; N64 and PS1 remain experimental.

ROMs, BIOS files and proprietary commercial game assets are not bundled.

With an authenticated StorCloud account, the unified player saves state to a per-user `auto` slot. Without login it falls back to local state export/import.

## PC Local Agent

The agent binds only to `127.0.0.1:47831` and exposes no arbitrary-command API.

Pairing flow:

```text
Logged-in browser
  -> 10-minute pair ticket
  -> localhost Local Agent
  -> StorCloud /agent/pair
  -> device credential stored locally by agent
```

Launch flow:

```text
Logged-in browser
  -> 45-second launch ticket for device + game_id
  -> localhost Local Agent
  -> agent validates ticket with StorCloud using its device credential
  -> allowlisted executable starts on local CPU/GPU
```

The browser never receives the permanent device credential and never sends an executable path.

## Documentation

- `docs/ARCHITECTURE.md` — local-first runtime model
- `docs/LOCAL-PC-RUNTIME.md` — native execution design and security model
- `docs/DEPLOYMENT.md` — Ubuntu deployment and verification
- `local-agent/README.md` — Local Agent installation and allowlist

## Legacy cleanup

Older development builds installed separate mGBA, FBNeo, N64, PPSSPP, SNES9x and BlastEm runtime directories. They are no longer served. `bash update.sh` removes those payloads automatically while preserving current browser-game packages such as Doom/FreeDoom.
