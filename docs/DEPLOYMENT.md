# StorCloud Deployment

## Ubuntu server

StorCloud v0.7 uses Docker Compose for PostgreSQL, FastAPI and the web launcher, with persistent private ROM and cloud-save storage.

```bash
cd /opt/storcloud
git pull
bash update.sh
```

`update.sh` performs these steps:

1. pulls the current `main` branch
2. creates/repairs `.env` with random persistent secrets and ROM limits
3. creates `storage/saves` and `storage/roms`
4. removes legacy separate Retro engine payloads
5. prepares browser-native game packages such as Doom/FreeDoom WASM
6. starts PostgreSQL and waits for its health check
7. rebuilds/restarts API and web services
8. checks API/database health and prints container status

## Services

- Web launcher: `http://SERVER_IP:8080`
- Minha Biblioteca: `http://SERVER_IP:8080/library/`
- Account/device dashboard: `http://SERVER_IP:8080/account/`
- Unified Retro player: `http://SERVER_IP:8080/retro/`
- PC Local: `http://SERVER_IP:8080/pc/`
- API: `http://SERVER_IP:8000`
- FastAPI docs: `http://SERVER_IP:8000/docs`

Expected containers:

- `storcloud-db`
- `storcloud-api`
- `storcloud-web`

## First administrator

The first update creates `/opt/storcloud/.env`. Read the first-admin setup token locally on the VM:

```bash
grep '^STORCLOUD_SETUP_TOKEN=' /opt/storcloud/.env
```

Open `/account/`, create the first account and provide this token. The token does not grant admin to later registrations once at least one user exists.

## Persistence

Do not remove these during ordinary upgrades:

- Docker volume `storcloud-postgres` — accounts, sessions, library metadata, devices, tickets and save metadata
- `/opt/storcloud/storage/saves` — cloud save-state files
- `/opt/storcloud/storage/roms` — private ROM library, separated by user ID
- `/opt/storcloud/runtime/games` — generated browser game packages
- `/opt/storcloud/.env` — database password and server settings

`docker compose down` is safe. `docker compose down -v` deletes the PostgreSQL volume and must not be used as a normal update command.

## ROM upload limit

Default per-file limit is 2 GiB:

```env
STORCLOUD_MAX_ROM_BYTES=2147483648
```

The bundled Nginx config also accepts request bodies up to 2 GiB and uses long API proxy timeouts. Change both the application setting and Nginx limit if you intentionally need larger files.

## HTTPS

For LAN HTTP testing, `STORCLOUD_COOKIE_SECURE=false` is expected. Before exposing StorCloud through a public HTTPS domain, set:

```env
STORCLOUD_COOKIE_SECURE=true
```

Then restart:

```bash
docker compose up -d --build
```

## Registration

Open registration is controlled in `.env`:

```env
STORCLOUD_ALLOW_REGISTRATION=true
```

Set it to `false` when you want only existing users to log in.

## Verify

```bash
cd /opt/storcloud
bash scripts/doctor.sh
```

Or manually:

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/setup/status
du -sh storage storage/saves storage/roms runtime
```

`/healthz` should report the API and database online.

## Full application backup

Use the bundled backup command:

```bash
cd /opt/storcloud
bash scripts/backup.sh
```

It creates:

- compressed PostgreSQL dump
- one compressed storage archive containing both `saves/` and `roms/`
- SHA-256 checksum file

Database metadata and storage files belong together for a complete restore.

## Legacy Retro cleanup

Older builds installed separate emulator payloads under `runtime/retro/` and `runtime/vendor/`. `scripts/cleanup-legacy-retro.sh` removes those legacy directories while preserving `runtime/games/`.

## Local Agent is not a central-server service

Install the StorCloud Local Agent on each player's Windows/Linux computer. Pair it from `/account/`. The central VM does not render PC Local sessions.

GitHub Actions builds Windows x64 and Linux x64 Local Agent artifacts whenever agent code changes.
