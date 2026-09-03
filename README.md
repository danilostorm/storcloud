# StorCloud

StorCloud is a local-first gaming platform. The control plane lives on the server, but games should execute on the player's device whenever technically possible.

## Execution modes

1. **Browser WASM** — games/engines already ported to WebAssembly run inside the browser with local CPU/GPU through WebGL/WebGPU.
2. **Unified Retro** — one Retro Library UI powered by Nostalgist.js + RetroArch Emscripten cores. Users never need to choose separate emulator applications.
3. **PC Local Agent** — normal Windows/Linux executables run on the player's own machine through a paired StorCloud agent and render with that machine's GPU.
4. **Remote streaming fallback** — Wolf/Sunshine-compatible streaming is reserved for titles that cannot execute locally.

An arbitrary Windows `.exe` cannot simply be converted to WebAssembly automatically. Browser-WASM is used for real ports; ordinary desktop games use the Local Agent path.

## Current stage

v0.4 Local First

### Available

- FastAPI control plane
- Docker deployment
- browser capability detection
- Doom/FreeDoom WASM proof of concept
- unified Retro Library at `/retro/`
- local ROM selection in the browser
- automatic platform/core selection for common retro formats
- save-state export/import and fullscreen controls

### Next

- StorCloud Local Agent for Windows/Linux
- paired-device authentication and allowlisted local game manifests
- multi-user accounts
- server-synchronized saves and library metadata
- covers, favorites, recent games and continue-playing
- additional browser-WASM PC ports
- remote streaming fallback

## Architecture

- `backend/api` — FastAPI control plane
- `frontend` — StorCloud launcher and unified players
- `games` — game manifests and browser assets
- `runtime` — generated runtime packages (not committed)
- `storage` — persistent server data (not committed)
- `docs` — architecture and integration notes

## Update

```bash
cd /opt/storcloud
bash update.sh
```

Then open:

- Web: `http://SERVER_IP:8080`
- Retro Library: `http://SERVER_IP:8080/retro/`
- API: `http://SERVER_IP:8000`
- API docs: `http://SERVER_IP:8000/docs`
