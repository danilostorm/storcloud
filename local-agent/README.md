# StorCloud Local Agent

The Local Agent is the native companion for PC games that cannot run directly in the browser as WebAssembly.

## v0.3 highlights

- process lifetime tracking for native PC games
- server-side play session starts after a successful local process spawn
- 30-second play-session heartbeat while the game process is alive
- automatic session end/playtime update when the process exits
- browser can be closed without losing native-game playtime tracking

## Security model

- binds only to `127.0.0.1:47831`
- reports local OS / architecture / CPU information
- reads an allowlisted local game catalog from JSON
- exposes only enabled game IDs/names to the browser
- never accepts an executable path or shell command from a website
- pairs with a logged-in StorCloud account using a short-lived ticket
- stores its per-device credential only in local `config/device.json`
- validates each launch using a 45-second one-time server ticket
- sends a device heartbeat to StorCloud every minute while paired

## Build

```bash
cargo build --release --manifest-path local-agent/Cargo.toml
```

CI produces Windows x64 and Linux x64 artifacts whenever the agent changes.

## Configure games

```bash
mkdir -p local-agent/config
cp local-agent/config/games.example.json local-agent/config/games.json
```

Example:

```json
{
  "games": [
    {
      "id": "my-game",
      "name": "My Game",
      "executable": "C:\\Games\\MyGame\\game.exe",
      "args": [],
      "working_dir": "C:\\Games\\MyGame",
      "enabled": true
    }
  ]
}
```

The executable path exists only in the local agent configuration. StorCloud web requests reference only `game_id`.

## Run

Linux:

```bash
export STORCLOUD_AGENT_GAMES="$PWD/local-agent/config/games.json"
export STORCLOUD_AGENT_DEVICE="$PWD/local-agent/config/device.json"
./local-agent/target/release/storcloud-local-agent
```

PowerShell:

```powershell
$env:STORCLOUD_AGENT_GAMES="$PWD\\local-agent\\config\\games.json"
$env:STORCLOUD_AGENT_DEVICE="$PWD\\local-agent\\config\\device.json"
.\\local-agent\\target\\release\\storcloud-local-agent.exe
```

Then open StorCloud `/account/` in the browser and click **Parear este PC**.

## Endpoints on localhost

- `GET /health` — health and paired state
- `GET /capabilities` — capability summary, including process tracking
- `GET /games` — enabled game IDs/names only
- `POST /pair` — consumes a StorCloud pairing ticket
- `POST /heartbeat` — manual device heartbeat trigger
- `POST /launch/{game_id}` — validates a one-time ticket and starts the allowlisted executable

## Launch and playtime flow

1. User logs in to StorCloud.
2. Browser chooses a paired device and allowlisted `game_id`.
3. StorCloud issues a 45-second launch ticket bound to user, device and game.
4. Browser passes that ticket to localhost.
5. Agent authenticates with its private device credential and consumes the ticket.
6. Agent starts the configured executable locally.
7. Agent creates a server play session and sends a 30-second heartbeat while the child process runs.
8. When the process exits, the agent closes the play session and StorCloud stores final playtime.

Rendering, DirectX/Vulkan and audio remain on the player's machine.
