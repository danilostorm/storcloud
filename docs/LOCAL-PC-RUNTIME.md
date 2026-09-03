# StorCloud Local PC Runtime

## Goal

Run PC games on the player's own machine whenever possible so rendering uses the player's CPU/GPU instead of the StorCloud server GPU.

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

The Local Agent is a small native companion installed on the player's machine. It will:

- pair with the user's StorCloud account/device
- advertise local capabilities (OS, CPU, GPU, RAM, supported runtimes)
- keep an allowlisted local game catalog
- download or validate user-owned game packages where permitted
- launch approved executables locally
- report session status, process exit and play time
- expose gamepad/overlay integration where useful
- synchronize saves with StorCloud when configured

The browser acts as the launcher/control plane; the game process itself renders normally on the player's local GPU.

## Important limitation

An arbitrary Windows `.exe` cannot be generically streamed to a browser and magically executed as WebAssembly. Windows x86/x64 games typically depend on Win32 APIs, DirectX, drivers and native code. They need one of:

- a real WebAssembly/source port
- a browser-compatible emulator/compatibility layer
- the StorCloud Local Agent on the player's machine
- remote streaming as a fallback

## Security model

The Local Agent must never expose an unauthenticated arbitrary-command endpoint.

Planned controls:

- bind locally only by default
- per-device pairing keys
- short-lived signed launch tickets from StorCloud
- executable allowlist/game manifests
- no shell command strings from the browser
- explicit paths and arguments defined by trusted manifests
- origin checks and replay protection
- optional user confirmation for first launch/install

## Launch decision

```text
Game selected
   |
   +-- Browser WASM available? --------> Run in browser (local GPU/CPU)
   |
   +-- Local Agent compatible? --------> Run native on player's PC (local GPU/CPU)
   |
   +-- Emulation/compat layer viable? -> Run locally through adapter
   |
   `-- Otherwise ----------------------> Remote streaming fallback
```

## Example: Need for Speed Underground

A normal retail Windows executable is not a direct WebAssembly package. The practical StorCloud path is Local Agent execution on the user's Windows/Linux compatibility environment. The browser launches the session; the local PC executes and renders the game.
