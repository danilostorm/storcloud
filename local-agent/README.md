# StorCloud Local Agent

The Local Agent is the native companion used when a PC game cannot run directly in the browser as WebAssembly.

## What it does

- binds only to `127.0.0.1:47831`
- reports local OS / architecture / CPU capability information
- reads an allowlisted game catalog from JSON
- launches games only by trusted `game_id`
- never accepts arbitrary shell commands from the browser
- requires a bearer token for game listing and launch endpoints

## Build

```bash
cargo build --release --manifest-path local-agent/Cargo.toml
```

Linux binary:

```text
local-agent/target/release/storcloud-local-agent
```

Windows binary:

```text
local-agent\\target\\release\\storcloud-local-agent.exe
```

## Configure

Copy the example catalog:

```bash
mkdir -p local-agent/config
cp local-agent/config/games.example.json local-agent/config/games.json
```

Set a strong token and the StorCloud web origin.

Linux/macOS:

```bash
export STORCLOUD_AGENT_TOKEN="replace-with-a-long-random-token"
export STORCLOUD_ORIGINS="http://192.168.30.8:8080"
export STORCLOUD_AGENT_GAMES="local-agent/config/games.json"
./local-agent/target/release/storcloud-local-agent
```

PowerShell:

```powershell
$env:STORCLOUD_AGENT_TOKEN="replace-with-a-long-random-token"
$env:STORCLOUD_ORIGINS="http://192.168.30.8:8080"
$env:STORCLOUD_AGENT_GAMES="local-agent\\config\\games.json"
.\\local-agent\\target\\release\\storcloud-local-agent.exe
```

## Endpoints

- `GET /health` — public loopback health check
- `GET /capabilities` — public loopback capability summary
- `GET /games` — requires bearer token
- `POST /launch/{game_id}` — requires bearer token

Example launch:

```bash
curl -X POST \
  -H "Authorization: Bearer $STORCLOUD_AGENT_TOKEN" \
  http://127.0.0.1:47831/launch/example-game
```

## Security note

This is an alpha foundation. Production pairing will replace the manually configured token with per-device pairing keys and short-lived signed launch tickets from StorCloud. The important security boundary is already enforced: the browser cannot submit an executable path or shell command; it can only reference an enabled allowlisted game ID.
