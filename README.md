# StorCloud

StorCloud is a hybrid browser gaming platform designed to run games through multiple execution modes:

- WebAssembly in the browser
- Retro emulation in the browser
- Local-device rendering where supported
- Remote streaming fallback for workloads that cannot run locally
- Multi-user library, saves and sessions

## Current stage

v0.1 Foundation

## Architecture

- `backend/api` - FastAPI control plane
- `frontend` - web launcher
- `games` - game manifests and web assets
- `engines` - WASM, emulator and streaming adapters
- `storage` - runtime data (not committed)

## Quick start

```bash
git pull
docker compose up -d --build
```

Then open:

- Web: `http://SERVER_IP:8080`
- API: `http://SERVER_IP:8000`
- API docs: `http://SERVER_IP:8000/docs`
