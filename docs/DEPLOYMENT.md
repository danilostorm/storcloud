# StorCloud Deployment

## Ubuntu server

StorCloud v0.8 uses Docker Compose for PostgreSQL, FastAPI and the web launcher, with persistent private ROM/save storage and a mounted hybrid execution catalog.

```bash
cd /opt/storcloud
git pull
bash update.sh
```

`update.sh` performs these steps:

1. pulls `main`
2. creates/repairs `.env` with persistent secrets and defaults
3. creates `storage/saves` and `storage/roms`
4. removes legacy separate Retro engine payloads
5. prepares browser-native game packages
6. starts PostgreSQL and waits for health
7. rebuilds/restarts API and web
8. checks API/database health and prints container status

## Web surfaces

- Home: `http://SERVER_IP:8080/`
- Hybrid Catalog: `http://SERVER_IP:8080/catalog/`
- Personal Library: `http://SERVER_IP:8080/library/`
- Account: `http://SERVER_IP:8080/account/`
- Retro Player: `http://SERVER_IP:8080/retro/`
- PC Local: `http://SERVER_IP:8080/pc/`
- Achievements: `http://SERVER_IP:8080/achievements/`
- Admin: `http://SERVER_IP:8080/admin/`
- Streaming fallback: `http://SERVER_IP:8080/stream/`
- API docs: `http://SERVER_IP:8000/docs`

Expected containers:

- `storcloud-db`
- `storcloud-api`
- `storcloud-web`

## First administrator

```bash
grep '^STORCLOUD_SETUP_TOKEN=' /opt/storcloud/.env
```

Open `/account/`, create the first account and provide that token.

## Persistence

Do not remove during normal upgrades:

- Docker volume `storcloud-postgres`
- `/opt/storcloud/storage/saves`
- `/opt/storcloud/storage/roms`
- `/opt/storcloud/runtime/games`
- `/opt/storcloud/.env`
- `/opt/storcloud/catalog/games.json`

`docker compose down` is safe. Do not use `docker compose down -v` for a normal update because it removes PostgreSQL data.

## ROM upload limit

Default per-file limit:

```env
STORCLOUD_MAX_ROM_BYTES=2147483648
```

The bundled Nginx config also allows up to 2 GiB request bodies.

## HTTPS

LAN testing:

```env
STORCLOUD_COOKIE_SECURE=false
```

For a public HTTPS domain:

```env
STORCLOUD_COOKIE_SECURE=true
```

Then rebuild:

```bash
docker compose up -d --build
```

## Registration

```env
STORCLOUD_ALLOW_REGISTRATION=true
```

Set to `false` to close new account creation.

## Streaming fallback

Disabled by default:

```env
STORCLOUD_STREAMING_ENABLED=false
STORCLOUD_STREAMING_PROVIDER=sunshine
STORCLOUD_STREAMING_HOST=
STORCLOUD_STREAMING_GATEWAY_TEMPLATE=
```

Supported provider values:

- `sunshine`
- `wolf`

Set `STORCLOUD_STREAMING_HOST` to the Moonlight-compatible rendering host when you actually have one available.

`STORCLOUD_STREAMING_GATEWAY_TEMPLATE` is optional. It is only needed when you have a compatible external web/client handoff layer. Supported placeholders are `{host}`, `{app_id}` and `{provider}`.

The central StorCloud VM still does not need a GPU for Browser WASM, Retro WASM or PC Local. A remote streaming host does need suitable rendering hardware for the games it serves.

## Verify

```bash
cd /opt/storcloud
bash scripts/doctor.sh
```

Manual checks:

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/catalog
curl -fsS http://127.0.0.1:8000/streaming/status
```

## Backup

```bash
cd /opt/storcloud
bash scripts/backup.sh
```

The backup contains:

- compressed PostgreSQL dump
- saves + private ROM storage archive
- SHA-256 checksum file

## Local Agent

Install the Local Agent on each player's Windows/Linux computer. Pair it from `/account/`.

Local Agent v0.3 tracks the spawned game process itself, so native-game playtime continues to be recorded even if the browser tab is closed.

GitHub Actions builds Windows x64 and Linux x64 artifacts whenever agent code changes.

## Legacy cleanup

Older separate mGBA, FBNeo, N64, PPSSPP, SNES9x and BlastEm payloads are removed automatically by `scripts/cleanup-legacy-retro.sh`.
