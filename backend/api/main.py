from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="StorCloud API", version="0.2.0")

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
            "name": "Retro Library",
            "type": "emulator",
            "engine": "multi-core",
            "rendering": "client",
            "status": "planned",
            "launch_url": "/retro/",
            "description": "SNES, GBA, Mega Drive, N64, PSP e Arcade via WebAssembly.",
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
        "version": "0.2.0",
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
