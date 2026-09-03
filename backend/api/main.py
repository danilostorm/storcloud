from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="StorCloud API", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNTIME_GAMES = Path("/runtime/games")


def installed(game_id: str) -> bool:
    return (RUNTIME_GAMES / game_id / "index.html").is_file()


RETRO_PLATFORMS = [
    {"id": "nes", "name": "Nintendo Entertainment System", "short": "NES", "core": "fceumm", "extensions": ["nes"]},
    {"id": "snes", "name": "Super Nintendo / Super Famicom", "short": "SNES", "core": "snes9x", "extensions": ["sfc", "smc"]},
    {"id": "gb", "name": "Game Boy / Game Boy Color", "short": "GB / GBC", "core": "mgba", "extensions": ["gb", "gbc"]},
    {"id": "gba", "name": "Game Boy Advance", "short": "GBA", "core": "mgba", "extensions": ["gba"]},
    {"id": "genesis", "name": "Mega Drive / Genesis", "short": "Mega Drive", "core": "genesis_plus_gx", "extensions": ["md", "gen"]},
    {"id": "sms", "name": "Master System", "short": "Master System", "core": "genesis_plus_gx", "extensions": ["sms"]},
    {"id": "gamegear", "name": "Game Gear", "short": "Game Gear", "core": "genesis_plus_gx", "extensions": ["gg"]},
    {"id": "arcade", "name": "Arcade / Neo Geo", "short": "Arcade", "core": "fbneo", "extensions": ["zip"]},
    {
        "id": "n64",
        "name": "Nintendo 64",
        "short": "N64",
        "core": "mupen64plus_next",
        "extensions": ["z64", "n64", "v64"],
        "experimental": True,
    },
    {
        "id": "ps1",
        "name": "PlayStation",
        "short": "PS1",
        "core": "pcsx_rearmed",
        "extensions": ["chd"],
        "experimental": True,
    },
]

EXECUTION_MODES = [
    {
        "id": "browser-wasm",
        "priority": 1,
        "rendering": "client",
        "description": "Real WebAssembly/WebGL/WebGPU ports run directly in the browser.",
    },
    {
        "id": "retro-wasm",
        "priority": 2,
        "rendering": "client",
        "description": "Unified RetroArch/Nostalgist player selects the core internally.",
    },
    {
        "id": "local-native",
        "priority": 3,
        "rendering": "client-native",
        "description": "StorCloud Local Agent launches allowlisted Windows/Linux games on the player's device.",
    },
    {
        "id": "remote-stream",
        "priority": 4,
        "rendering": "remote-host",
        "description": "Fallback only when no local execution route is viable.",
    },
]


def game_catalog():
    doom_ready = installed("doom-wasm")
    return [
        {
            "id": "doom-wasm",
            "name": "Doom / FreeDoom WASM",
            "type": "wasm",
            "engine": "Chocolate Doom + Emscripten",
            "rendering": "client",
            "status": "ready" if doom_ready else "installing",
            "launch_url": "/games/doom-wasm/",
            "description": "Executa WebAssembly diretamente no navegador usando CPU/GPU do dispositivo do jogador.",
        },
        {
            "id": "retro",
            "name": "Retro Library",
            "type": "emulator",
            "engine": "Nostalgist.js + RetroArch WASM",
            "rendering": "client",
            "status": "ready",
            "launch_url": "/retro/",
            "description": "Uma biblioteca e um player únicos. O StorCloud escolhe o core automaticamente sem expor emuladores separados ao usuário.",
        },
        {
            "id": "pc-local",
            "name": "PC Local",
            "type": "local",
            "engine": "StorCloud Local Agent",
            "rendering": "client-native",
            "status": "alpha",
            "launch_url": "/pc/",
            "description": "Jogos Windows/Linux executados no computador do jogador e renderizados pela GPU local. O agente alpha já faz detecção e lançamento por allowlist.",
        },
        {
            "id": "pc-wasm",
            "name": "PC WebAssembly",
            "type": "wasm",
            "engine": "WASM / WebGL / WebGPU",
            "rendering": "client",
            "status": "active-track",
            "launch_url": None,
            "description": "Ports e engines de PC compilados para WebAssembly executam 100% no navegador quando tecnicamente compatíveis.",
        },
        {
            "id": "remote-stream",
            "name": "Streaming Fallback",
            "type": "stream",
            "engine": "Wolf / Sunshine compatible",
            "rendering": "remote-host",
            "status": "fallback",
            "launch_url": None,
            "description": "Último recurso para títulos que não podem executar localmente no navegador ou no agente do jogador.",
        },
    ]


@app.get("/")
def root():
    return {
        "name": "StorCloud",
        "version": "0.5.0",
        "status": "online",
        "modes": [mode["id"] for mode in EXECUTION_MODES],
        "strategy": "local-first",
    }


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/games")
def list_games():
    games = game_catalog()
    return {"items": games, "count": len(games)}


@app.get("/retro/platforms")
def list_retro_platforms():
    return {
        "items": RETRO_PLATFORMS,
        "count": len(RETRO_PLATFORMS),
        "player": "unified",
        "runtime": "Nostalgist.js + RetroArch Emscripten",
        "execution": "client",
        "roms_included": False,
    }


@app.get("/runtime/strategy")
def runtime_strategy():
    return {"strategy": "local-first", "modes": EXECUTION_MODES}


@app.get("/capabilities")
def capabilities():
    return {
        "wasm": True,
        "webgl": True,
        "webgpu": "client-detected",
        "retro_emulation": "client-unified",
        "local_agent": "alpha",
        "local_agent_bind": "127.0.0.1:47831",
        "remote_streaming": "fallback",
        "server_gpu_required_for_wasm": False,
        "server_gpu_required_for_local_agent": False,
    }
