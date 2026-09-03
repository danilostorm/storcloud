# StorCloud

StorCloud is a **local-first multi-user gaming platform**. The central server owns accounts, private libraries, devices, saves, activity, achievements and launch authorization. Rendering should happen on the player's hardware whenever possible.

## v0.8 Platform

Execution priority:

1. **Browser WASM / WebGPU** — real browser ports run on the player's CPU/GPU.
2. **Retro WASM** — one unified Nostalgist.js + RetroArch player; cores are hidden implementation details.
3. **PC Local** — StorCloud Local Agent launches allowlisted Windows/Linux games on the player's machine.
4. **Remote Streaming** — Wolf/Sunshine/Moonlight-compatible fallback only when no local route is available.

An arbitrary Windows `.exe` is not automatically converted to WebAssembly. Native games need a real browser port, the Local Agent, a compatibility/emulation layer or remote streaming.

## Included now

### Multi-user control plane

- PostgreSQL persistent database
- registration/login with HttpOnly sessions
- first-admin setup token
- admin dashboard and account controls
- private ROM library per user
- cloud save states per user/game/slot
- paired PC devices and revocation

### Retro

- unified Retro Library/player
- NES, SNES, GB/GBC, GBA, Mega Drive, Master System, Game Gear and Arcade mappings
- N64 and PS1 experimental mappings
- private ROM upload up to 2 GiB by default
- SHA-256 duplicate detection
- favorites and last-played metadata
- direct launch from Personal Library
- cloud save + local export/import fallback
- play-session tracking and Continue Playing

### PC Local

- Rust Local Agent v0.3
- loopback-only browser API on `127.0.0.1:47831`
- allowlisted local executable catalog
- 10-minute account pairing tickets
- per-device private credential stored only by the agent
- 45-second one-time launch tickets
- local process lifetime tracking
- 30-second playtime heartbeat while a native game process runs
- automatic session end when the process exits
- Windows x64 and Linux x64 CI builds

### Platform experience

- Continue Playing on Home
- total playtime/session/game metrics
- achievements
- admin overview/users/activity
- hybrid execution manifests in `catalog/games.json`
- automatic route resolver based on WASM, WebGPU, Local Agent and streaming availability
- streaming fallback descriptor for Wolf/Sunshine-compatible hosts

### Operations

- automatic legacy separate-emulator cleanup
- PostgreSQL + ROM + save backups
- `doctor.sh` for Docker/database/catalog/streaming/storage checks
- Server CI with PostgreSQL integration smoke tests

## Update the Ubuntu server

```bash
cd /opt/storcloud
git pull
bash update.sh
```

Open:

- Home: `http://SERVER_IP:8080/`
- Hybrid Catalog: `http://SERVER_IP:8080/catalog/`
- Personal Library: `http://SERVER_IP:8080/library/`
- Retro Player: `http://SERVER_IP:8080/retro/`
- PC Local: `http://SERVER_IP:8080/pc/`
- Achievements: `http://SERVER_IP:8080/achievements/`
- Account: `http://SERVER_IP:8080/account/`
- Admin: `http://SERVER_IP:8080/admin/`
- Streaming fallback: `http://SERVER_IP:8080/stream/`
- API docs: `http://SERVER_IP:8000/docs`

## First administrator

On the first multi-user deployment:

```bash
grep '^STORCLOUD_SETUP_TOKEN=' /opt/storcloud/.env
```

Open `/account/` and use that token when creating the first account.

## Hybrid catalog

`catalog/games.json` defines routes per title. A game can expose multiple execution routes with priorities, for example:

```text
browser-wasm priority 100
local-native priority 50
remote-stream priority 10
```

The API resolver evaluates client/instance capabilities and returns the highest-priority route that is actually available.

Endpoints:

- `GET /api/catalog`
- `POST /api/catalog/{game_id}/resolve`

## Streaming fallback

Streaming is disabled by default. Wolf and Sunshine are Moonlight/GameStream-compatible servers; StorCloud treats them as a fallback transport rather than pretending they are ordinary browser video endpoints.

`.env` options:

```env
STORCLOUD_STREAMING_ENABLED=false
STORCLOUD_STREAMING_PROVIDER=sunshine
STORCLOUD_STREAMING_HOST=
STORCLOUD_STREAMING_GATEWAY_TEMPLATE=
```

`STORCLOUD_STREAMING_PROVIDER` supports `sunshine` or `wolf`.

If a separate compatible web/client gateway exists, `STORCLOUD_STREAMING_GATEWAY_TEMPLATE` can contain:

- `{host}`
- `{app_id}`
- `{provider}`

Without a gateway, StorCloud still resolves the remote host/app descriptor but reports that a Moonlight-compatible client handoff is required.

## Persistent data

Do not remove during upgrades:

- Docker volume `storcloud-postgres`
- `/opt/storcloud/storage/saves`
- `/opt/storcloud/storage/roms`
- `/opt/storcloud/runtime/games`
- `/opt/storcloud/.env`

## Operations

Diagnostics:

```bash
cd /opt/storcloud
bash scripts/doctor.sh
```

Backup database + saves + private ROM library:

```bash
bash scripts/backup.sh
```

## Repository layout

```text
backend/api/                  FastAPI modular control plane
catalog/games.json            hybrid execution manifests
frontend/                     web experiences
frontend/admin/               administrator dashboard
frontend/achievements/        achievements UI
frontend/catalog/             route-resolving catalog
frontend/library/             personal Retro collection
frontend/retro/               unified Retro player
frontend/pc/                  Local Agent launcher
frontend/stream/              remote fallback handoff
local-agent/                  Rust native companion
runtime/                      generated browser-game payloads
storage/saves/                cloud save binaries
storage/roms/                 private user ROM library
scripts/                      deploy, backup, diagnostics, cleanup
```

## Legal/content boundary

StorCloud does not bundle commercial ROMs, BIOS images or proprietary game data. Users provide files they are authorized to use. Browser/source-port integrations should respect upstream licenses and game-data requirements.
