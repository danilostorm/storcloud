# StorCloud Architecture

## Product rule: local first

StorCloud is a control plane first. Rendering should happen on the player's device whenever a viable local execution path exists.

Execution priority:

1. **Browser WASM / WebGPU** — real browser ports and engines.
2. **Retro WASM** — one unified Nostalgist.js + RetroArch Emscripten player.
3. **Local Native** — StorCloud Local Agent launches allowlisted Windows/Linux games on the player's machine.
4. **Remote Streaming** — Wolf/Sunshine/Moonlight-compatible fallback only when no local route is viable.

```text
Game manifest
    |
    v
Route resolver
    |
    +-- browser-wasm available? ----> browser / local CPU+GPU
    +-- retro-wasm available? ------> unified Retro player / local CPU+GPU
    +-- local-native available? ----> Local Agent / local CPU+GPU
    `-- remote-stream available? ---> Wolf/Sunshine host
```

## Hybrid manifest layer

`catalog/games.json` is the execution catalog. A game may expose several routes, each with a priority and requirements.

Examples of requirements:

- `wasm`
- `webgpu`
- `local_agent`
- `remote_stream`
- `package:<slug>` for a server-delivered browser package

`POST /api/catalog/{game_id}/resolve` receives the client capabilities and returns the highest-priority route that is currently available, plus the evaluated/missing requirements.

This keeps routing logic out of individual pages and makes Browser WASM, Local Agent and remote fallback coexist under one game identity.

## Server responsibilities

- web launcher and API
- users, sessions and permissions
- private game/ROM library metadata
- device pairing and launch authorization
- hybrid game manifests
- delivery of permitted browser game packages
- cloud saves
- playtime/history/Continue Playing
- achievements
- admin metrics and user controls
- streaming fallback descriptors

The StorCloud server does **not** need a GPU for Browser WASM, Retro WASM or Local Agent execution.

## Browser WASM / WebGPU

Use this mode only when a game or engine has an actual browser-compatible port. Typical technologies:

- WebAssembly / Emscripten
- WebGL
- WebGPU
- browser audio and gamepad APIs

An arbitrary Windows executable cannot be automatically converted to WebAssembly.

## Retro Library

Users choose games, not emulator applications. Platform/core mapping is internal:

- NES → fceumm
- SNES → snes9x
- GB/GBC/GBA → mgba
- Mega Drive / Master System / Game Gear → genesis_plus_gx
- Arcade / Neo Geo → fbneo
- N64 → mupen64plus_next (experimental)
- PS1 → pcsx_rearmed (experimental)

Private uploaded ROMs live in per-user server storage. Commercial ROMs, BIOS files and proprietary game data are not bundled.

The Retro player opens a play session after the emulator starts, sends heartbeats and closes the session on exit/page leave. This powers history, playtime, achievements and Continue Playing.

## Local Native / PC games

Local Agent v0.3:

- binds only to `127.0.0.1:47831`
- pairs using a short-lived server ticket
- stores the permanent device credential only locally
- exposes only allowlisted game IDs/names
- never accepts shell commands or executable paths from the website
- validates a one-time launch ticket before each process spawn
- creates a server play session after spawn
- heartbeats while the child process is alive
- closes the session when the process exits

The browser can close without losing native-game playtime tracking.

## Remote streaming

Remote streaming is deliberately last in the route resolver.

StorCloud supports provider descriptors for:

- Sunshine
- Wolf

Both are treated as Moonlight-compatible transports. StorCloud does not claim that GameStream/Moonlight is a native browser `<video>` protocol.

Configuration is controlled through `.env`. If an external compatible web/client gateway is available, `STORCLOUD_STREAMING_GATEWAY_TEMPLATE` can provide a handoff URL. Otherwise StorCloud returns the provider/host/app descriptor and reports that a Moonlight-compatible client is required.

## Persistence

- PostgreSQL: users, sessions, devices, tickets, ROM metadata, save metadata, play sessions and achievements
- `storage/roms`: private user ROM files
- `storage/saves`: cloud save-state files
- `runtime/games`: generated/downloaded browser game packages
- `.env`: instance secrets and optional streaming configuration

Legacy `runtime/retro/*` separate emulator payloads are removed by `scripts/cleanup-legacy-retro.sh`.
