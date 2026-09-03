# StorCloud Architecture

## Product rule: local first

StorCloud is a control plane and library first. Rendering should happen on the player's device whenever a viable local execution path exists.

Execution priority:

1. **Browser WASM / WebGPU** — real browser ports and engines.
2. **Retro WASM** — one unified Retro Library powered by Nostalgist.js + RetroArch Emscripten cores.
3. **Local Native** — StorCloud Local Agent launches allowlisted Windows/Linux games on the player's machine.
4. **Remote Streaming** — Wolf/Sunshine-compatible fallback only when no local route is viable.

```text
Game selected
   |
   +-- real browser WASM/WebGPU port? ---> Browser / local CPU+GPU
   |
   +-- retro platform supported? --------> Unified Retro player / local CPU+GPU
   |
   +-- Local Agent compatible? ----------> Native PC process / local CPU+GPU
   |
   `-- otherwise ------------------------> Remote streaming fallback
```

## Server responsibilities

- web launcher and API
- users, device pairing and permissions
- game metadata and manifests
- delivery of permitted browser game packages
- save synchronization and session metadata
- routing decisions
- optional remote-stream orchestration

The StorCloud server does **not** need a GPU for Browser WASM, Retro WASM or Local Agent execution.

## Browser WASM / WebGPU

Use this mode only when a game or engine has an actual browser-compatible port. Typical technologies:

- WebAssembly / Emscripten
- WebGL
- WebGPU
- browser audio and gamepad APIs

An arbitrary Windows executable cannot be automatically converted into WebAssembly. Win32/DirectX/native dependencies require a real port, compatibility layer, Local Agent or remote streaming.

## Retro Library

StorCloud exposes one Retro Library and one player. Users select a ROM; the platform/core mapping is internal.

Initial platform map:

- NES → fceumm
- SNES → snes9x
- GB/GBC/GBA → mgba
- Mega Drive / Master System / Game Gear → genesis_plus_gx
- Arcade / Neo Geo → fbneo
- Nintendo 64 → mupen64plus_next (experimental)
- PlayStation → pcsx_rearmed (experimental)

ROMs, BIOS files and commercial game data are not bundled by StorCloud.

## Local Native / PC games

The StorCloud Local Agent is a native companion installed on the player's computer. It binds to loopback only and launches only allowlisted game IDs.

Current alpha endpoints:

- `GET http://127.0.0.1:47831/health`
- `GET http://127.0.0.1:47831/capabilities`
- authenticated `GET /games`
- authenticated `POST /launch/{game_id}`

See `LOCAL-PC-RUNTIME.md` and `../local-agent/README.md`.

## Remote streaming

Remote streaming is deliberately last in the decision tree. It is intended for games that cannot be executed locally through a browser port, retro core or Local Agent-compatible native runtime.

Planned adapters can target Wolf/Sunshine/Moonlight-compatible infrastructure without making that architecture mandatory for the rest of the platform.

## Runtime storage

`runtime/` contains generated/downloaded runtime payloads and is not committed.

- `runtime/games/doom-wasm/` — current browser WASM demo package
- legacy `runtime/retro/*` separate engines are removed by `scripts/cleanup-legacy-retro.sh`

The unified Retro player lives in `frontend/retro/`; it does not require one server directory per emulator.
