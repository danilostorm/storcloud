# StorCloud Deployment

## Ubuntu server

Current deployment uses Docker Compose for the API and web launcher.

```bash
cd /opt/storcloud
git pull
bash update.sh
```

`update.sh` performs these steps:

1. pulls the current `main` branch
2. removes legacy separate Retro engine payloads
3. prepares browser-native game packages such as Doom/FreeDoom WASM
4. rebuilds/restarts Docker services
5. prints container status

## Services

- Web launcher: `http://SERVER_IP:8080`
- Unified Retro Library: `http://SERVER_IP:8080/retro/`
- PC Local status page: `http://SERVER_IP:8080/pc/`
- API: `http://SERVER_IP:8000`
- FastAPI docs: `http://SERVER_IP:8000/docs`

## Legacy Retro cleanup

Older StorCloud development builds installed separate emulator payloads under `runtime/retro/` and `runtime/vendor/`.

The following legacy IDs are cleaned automatically:

- snes9x
- mgba / mGBA-wasm
- blastem / blastem-wasm
- fbneo / fbneo-wasm
- n64 / n64wasm / N64Wasm
- ppsspp / ppsspp-wasm

The cleanup intentionally preserves `runtime/games/`, including Doom/FreeDoom WASM.

Manual cleanup, if ever needed:

```bash
cd /opt/storcloud
bash scripts/cleanup-legacy-retro.sh
```

## Verify

```bash
docker compose ps
curl -fsS http://127.0.0.1:8000/healthz
find runtime -maxdepth 2 -type d -print
```

Expected containers:

- `storcloud-api`
- `storcloud-web`

## Local Agent is not a server service

The StorCloud Local Agent is installed on each player's Windows/Linux computer, not on the central StorCloud VM. Building it on the server is useful only for development/testing.

Linux development build:

```bash
bash scripts/build-local-agent.sh
```

GitHub Actions also builds Windows x64 and Linux x64 artifacts automatically when Local Agent code changes.
