# StorCloud

StorCloud is a **local-first multi-user gaming platform**. The server organizes accounts, private libraries, devices, saves and launch authorization, while games should render on the player's own hardware whenever possible.

## v0.7 Personal Library

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
- private ROM library per user
- SHA-256 duplicate detection for uploaded ROMs
- favorite and last-played metadata
- up to 2 GiB per ROM by default, configurable
- direct launch from **Minha Biblioteca** into the unified Retro player
- stable per-library-game cloud-save key
- cloud save-state storage per user/game/slot
- local-file Retro mode without server upload
- user/device model
- 10-minute Local Agent pairing tickets
- per-device credentials stored only by the Local Agent
- 45-second one-time PC launch tickets
- Local Agent heartbeat/device presence
- Doom / FreeDoom browser-WASM package bootstrap
- PC Local launch UI
- Rust Local Agent v0.2
- Windows/Linux Local Agent CI builds
- API/PostgreSQL integration smoke test, including private ROM upload/download
- server doctor and database/storage backup scripts
- automatic cleanup of old separate-emulator payloads

## Update the Ubuntu server

```bash
cd /opt/storcloud
git pull
bash update.sh
```

`update.sh` creates `.env` on first run with a random PostgreSQL password and first-admin setup token, creates save/ROM storage, cleans legacy retro payloads, prepares browser games, rebuilds containers and checks API/database health.

Open:

- Launcher: `http://SERVER_IP:8080`
- Minha Biblioteca: `http://SERVER_IP:8080/library/`
- Account: `http://SERVER_IP:8080/account/`
- Retro player: `http://SERVER_IP:8080/retro/`
- PC Local: `http://SERVER_IP:8080/pc/`
- API: `http://SERVER_IP:8000`
- API docs: `http://SERVER_IP:8000/docs`

## First administrator

After the first multi-user update, read the generated setup token on the VM:

```bash
grep '^STORCLOUD_SETUP_TOKEN=' /opt/storcloud/.env
```

Open `/account/`, create the first account and provide that token. Only the first account can become admin this way.

## Personal Retro library

Log in and open `/library/`.

The current library supports:

- NES: `.nes`
- SNES: `.sfc`, `.smc`
- Game Boy / GBC: `.gb`, `.gbc`
- Game Boy Advance: `.gba`
- Mega Drive / Genesis: `.md`, `.gen`
- Master System: `.sms`
- Game Gear: `.gg`
- Arcade / Neo Geo: `.zip`
- N64 experimental: `.z64`, `.n64`, `.v64`
- PS1 experimental: `.chd`

The user provides their own files. StorCloud does not bundle commercial ROMs, BIOS images or proprietary game data.

Library files are private to the authenticated account. The API stores them under `storage/roms/<user-id>/`; metadata and SHA-256 hashes live in PostgreSQL.

Clicking **Jogar** opens `/retro/?rom=<id>`. The unified player uses the authenticated ROM URL directly instead of creating a second full copy in browser JavaScript memory.

## Persistent data

- PostgreSQL: Docker volume `storcloud-postgres`
- cloud save files: `/opt/storcloud/storage/saves`
- private ROM library: `/opt/storcloud/storage/roms`
- browser game payloads: `/opt/storcloud/runtime/games`
- server secrets: `/opt/storcloud/.env` (ignored by Git)

Do not delete the PostgreSQL volume or `storage/` when updating.

## Operations

Health check:

```bash
cd /opt/storcloud
bash scripts/doctor.sh
```

Backup database + saves + private ROM library:

```bash
cd /opt/storcloud
bash scripts/backup.sh
```

Backups are written to `backups/` by default and include SHA-256 checksums.

## Repository layout

```text
backend/api/                  FastAPI multi-user control plane
frontend/                     web launcher
frontend/account/             login, device pairing and save dashboard
frontend/library/             private per-user Retro collection
frontend/retro/               unified Retro player + cloud saves
frontend/pc/                  Local Agent pairing/launch experience
local-agent/                  native Rust companion for PC games
runtime/                      generated/downloaded browser payloads; not committed
storage/saves/                persistent cloud save files
storage/roms/                 persistent private ROM library
scripts/bootstrap-env.sh      generates persistent server secrets/storage
scripts/bootstrap-games.sh    browser game package installer
scripts/cleanup-legacy-retro.sh
scripts/doctor.sh
scripts/backup.sh
update.sh                     Ubuntu update/deploy entrypoint
docs/                         architecture and operations documentation
```

## Retro

The user chooses a game, not an emulator. StorCloud maps the platform to the appropriate RetroArch WebAssembly core internally.

With an authenticated account, library games use a stable `rom-<id>` cloud-save key. Without login or when using a local-only ROM, the player can still export/import states locally.

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
