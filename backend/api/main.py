from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="StorCloud API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNTIME_GAMES = Path("/runtime/games")
RUNTIME_RETRO = Path("/runtime/retro")


def installed(game_id: str) -> bool:
    return (RUNTIME_GAMES / game_id / "index.html").is_file()


def retro_installed(engine_id: str) -> bool:
    return (RUNTIME_RETRO / engine_id / "index.html").is_file()


RETRO_ENGINES = [
    {
        "id": "snes9x",
        "name": "Super Nintendo",
        "systems": ["SNES", "Super Famicom"],
        "engine": "SNES9x WASM",
        "rendering": "client",
        "launch_url": "/retro/engines/snes9x/",
        "description": "SNES9x em WebAssembly, com gamepad, áudio local, save states e persistência no navegador.",
    },
    {
        "id": "mgba",
        "name": "Game Boy / Game Boy Advance",
        "systems": ["GBA", "GB", "GBC"],
        "engine": "mGBA WASM",
        "rendering": "client",
        "launch_url": "/retro/engines/mgba/",
        "description": "mGBA em WebAssembly para GBA, Game Boy e Game Boy Color, incluindo ROMs compactadas compatíveis.",
    },
    {
        "id": "blastem",
        "name": "Mega Drive / Genesis",
        "systems": ["Mega Drive", "Genesis"],
        "engine": "BlastEm WASM",
        "rendering": "client",
        "launch_url": "/retro/engines/blastem/",
        "description": "BlastEm compilado para WebAssembly para jogos de Mega Drive/Genesis usando o hardware do jogador.",
    },
    {
        "id": "fbneo",
        "name": "Arcade",
        "systems": ["Arcade", "Neo Geo"],
        "engine": "FinalBurn Neo WASM",
        "rendering": "client",
        "launch_url": "/retro/engines/fbneo/",
        "description": "FinalBurn Neo em WebAssembly para um grande catálogo de placas arcade e Neo Geo.",
    },
    {
        "id": "n64",
        "name": "Nintendo 64",
        "systems": ["N64"],
        "engine": "N64Wasm / ParaLLEl",
        "rendering": "client",
        "launch_url": "/retro/engines/n64/",
        "description": "Port web do core ParaLLEl com gamepad, save states, SRAM, fullscreen e controles móveis.",
    },
    {
        "id": "ppsspp",
        "name": "PlayStation Portable",
        "systems": ["PSP"],
        "engine": "PPSSPP WASM",
        "rendering": "client",
        "launch_url": None,
        "description": "Slot PSP preparado. O SDK wasm-gaming existe, mas o runtime nativo ainda não está distribuído por esse projeto; integração de um port executável fica isolada deste núcleo.",
        "experimental": True,
    },
]


def retro_catalog():
    items = []
    for engine in RETRO_ENGINES:
        item = dict(engine)
        if engine.get("experimental"):
            item["status"] = "experimental"
        else:
            item["status"] = "ready" if retro_installed(engine["id"]) else "installing"
        items.append(item)
    return items


def game_catalog():
    doom_ready = installed("doom-wasm")
    retro_ready = any(item["status"] == "ready" for item in retro_catalog())
    return [
        {
            "id": "doom-wasm",
            "name": "Doom / FreeDoom WASM",
            "type": "wasm",
            "engine": "Chocolate Doom + Emscripten",
            "rendering": "client",
            "status": "ready" if doom_ready else "installing",
            "launch_url": "/games/doom-wasm/",
            "description": "Executa WebAssembly no navegador e usa CPU/GPU do dispositivo do jogador.",
        },
        {
            "id": "quake-wasm",
            "name": "Quake WASM",
            "type": "wasm",
            "engine": "Emscripten",
            "rendering": "client",
            "status": "planned",
            "launch_url": "/games/quake-wasm/",
            "description": "Próximo engine WASM da biblioteca nativa.",
        },
        {
            "id": "retro",
            "name": "Retro Hub",
            "type": "emulator",
            "engine": "multi-engine",
            "rendering": "client",
            "status": "ready" if retro_ready else "installing",
            "launch_url": "/retro/",
            "description": "SNES, GBA, Game Boy, Mega Drive, Arcade e N64 via WebAssembly, com PSP em integração experimental.",
        },
        {
            "id": "local-runtime",
            "name": "Local Runtime",
            "type": "local",
            "engine": "StorCloud Bridge",
            "rendering": "client-native",
            "status": "research",
            "launch_url": None,
            "description": "Camada futura para executáveis compatíveis renderizarem na máquina do usuário.",
        },
    ]


@app.get("/")
def root():
    return {
        "name": "StorCloud",
        "version": "0.3.0",
        "status": "online",
        "modes": ["wasm", "emulator", "local", "stream"],
    }


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/games")
def list_games():
    games = game_catalog()
    return {"items": games, "count": len(games)}


@app.get("/retro/engines")
def list_retro_engines():
    engines = retro_catalog()
    return {
        "items": engines,
        "count": len(engines),
        "execution": "client",
        "roms_included": False,
    }


@app.get("/capabilities")
def capabilities():
    return {
        "wasm": True,
        "webgpu": "client-detected",
        "emulation": True,
        "local_runtime": "experimental",
        "streaming": "planned",
        "server_gpu_required_for_wasm": False,
    }
