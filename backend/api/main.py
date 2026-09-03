from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="StorCloud API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

GAMES = [
    {
        "id": "doom-wasm",
        "name": "Doom WASM",
        "type": "wasm",
        "engine": "emscripten",
        "status": "planned",
        "launch_url": "/games/doom-wasm/",
    },
    {
        "id": "quake-wasm",
        "name": "Quake WASM",
        "type": "wasm",
        "engine": "emscripten",
        "status": "planned",
        "launch_url": "/games/quake-wasm/",
    },
    {
        "id": "retro",
        "name": "Retro Library",
        "type": "emulator",
        "engine": "multi-core",
        "status": "planned",
        "launch_url": "/retro/",
    },
]


@app.get("/")
def root():
    return {
        "name": "StorCloud",
        "version": "0.1.0",
        "status": "online",
        "modes": ["wasm", "emulator", "local", "stream"],
    }


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/games")
def list_games():
    return {"items": GAMES, "count": len(GAMES)}


@app.get("/capabilities")
def capabilities():
    return {
        "wasm": True,
        "webgpu": "client-detected",
        "emulation": True,
        "local_runtime": "experimental",
        "streaming": "planned",
    }
