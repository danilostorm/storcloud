# StorCloud Local PC Runtime

## Goal

Run PC games on the player's own machine whenever possible so rendering uses the player's CPU/GPU instead of the StorCloud server GPU.

## Current status

The Local Agent is now implemented as an **alpha Rust companion** in `local-agent/`.

Current alpha capabilities:

- binds only to `127.0.0.1:47831`
- reports OS, architecture and logical CPU count
- reads an allowlisted local game catalog
- requires a bearer token for game listing and launching
- launches by trusted `game_id`, never by arbitrary shell command/path from the browser
- has Windows x64 and Linux x64 CI builds
- has a web status page at `/pc/`

Still planned for the production agent:

- account/device pairing flow
- short-lived signed launch tickets instead of a manually configured bearer token
- GPU/RAM/runtime inventory
- install/download adapters for permitted user-owned packages
- process/session telemetry
- save synchronization
- gamepad/overlay integrations
- Windows service / Linux user-service installers

## Two local execution paths

### 1. Browser WASM / WebGPU

Use this path only when a game or engine has a real browser/WebAssembly port.

Examples:

- source ports compiled with Emscripten
- engines with WebAssembly builds
- browser-native games
- WebGL/WebGPU renderers

The server only delivers the package and metadata. Execution and rendering happen inside the browser.

### 2. StorCloud Local Agent

Use this path for ordinary Windows/Linux desktop games that cannot run directly in the browser.

The browser acts as the launcher/control plane; the native game process itself renders normally on the player's local GPU.

## Important limitation

An arbitrary Windows `.exe` cannot be generically streamed to a browser and magically executed as WebAssembly. Windows x86/x64 games typically depend on Win32 APIs, DirectX, drivers and native code. They need one of:

- a real WebAssembly/source port
- a browser-compatible emulator/compatibility layer
- the StorCloud Local Agent on the player's machine
- remote streaming as a fallback

## Security model

Already enforced in alpha:

- loopback-only bind by default
- executable allowlist/game manifests
- no shell command strings from the browser
- no executable path accepted by launch requests
- bearer-token protection for private endpoints
- configurable allowed web origins

Production hardening planned:

- per-device pairing keys
- short-lived signed launch tickets from StorCloud
- replay protection
- optional user confirmation for first launch/install
- tighter origin/device binding

## Launch decision

```text
Game selected
   |
   +-- Browser WASM available? --------> Run in browser (local GPU/CPU)
   |
   +-- Retro platform supported? -----> Run unified Retro WASM player
   |
   +-- Local Agent compatible? --------> Run native on player's PC (local GPU/CPU)
   |
   `-- Otherwise ----------------------> Remote streaming fallback
```

## Example: Need for Speed Underground

A normal retail Windows executable is not a direct WebAssembly package. The practical StorCloud path is Local Agent execution on the user's Windows/Linux compatibility environment. The browser launches the session; the local PC executes and renders the game.
