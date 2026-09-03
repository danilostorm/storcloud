import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/catalog", tags=["catalog"])
CATALOG_PATH = Path(os.getenv("STORCLOUD_CATALOG_PATH", "/catalog/games.json"))
RUNTIME_GAMES = Path("/runtime/games")


class ClientCapabilities(BaseModel):
    wasm: bool = True
    webgpu: bool = False
    local_agent: bool = False
    remote_stream: bool = False


def load_catalog() -> dict:
    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 1, "games": []}
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=500, detail=f"catalog unavailable: {error}")


def requirement_available(requirement: str, caps: ClientCapabilities) -> bool:
    if requirement == "wasm":
        return caps.wasm
    if requirement == "webgpu":
        return caps.webgpu
    if requirement == "local_agent":
        return caps.local_agent
    if requirement == "remote_stream":
        return caps.remote_stream
    if requirement.startswith("package:"):
        package = requirement.split(":", 1)[1]
        return (RUNTIME_GAMES / package / "index.html").is_file()
    return False


def route_status(route: dict, caps: ClientCapabilities) -> tuple[bool, list[str]]:
    missing = [req for req in route.get("requires", []) if not requirement_available(req, caps)]
    return not missing, missing


@router.get("")
def list_catalog():
    catalog = load_catalog()
    return {"version": catalog.get("version", 1), "items": catalog.get("games", []), "count": len(catalog.get("games", []))}


@router.post("/{game_id}/resolve")
def resolve_game(game_id: str, caps: ClientCapabilities):
    catalog = load_catalog()
    game = next((item for item in catalog.get("games", []) if item.get("id") == game_id), None)
    if not game:
        raise HTTPException(status_code=404, detail="game manifest not found")

    evaluated = []
    for route in sorted(game.get("routes", []), key=lambda item: item.get("priority", 0), reverse=True):
        available, missing = route_status(route, caps)
        evaluated.append({**route, "available": available, "missing": missing})
        if available:
            launch_url = route.get("launch_url")
            if route.get("mode") == "remote-stream":
                launch_url = f"/stream/?game={game_id}"
            return {
                "game": {key: value for key, value in game.items() if key != "routes"},
                "decision": {
                    **route,
                    "available": True,
                    "missing": [],
                    "launch_url": launch_url,
                },
                "evaluated": evaluated,
            }

    return {
        "game": {key: value for key, value in game.items() if key != "routes"},
        "decision": None,
        "evaluated": evaluated,
        "reason": "no execution route is currently available on this client/instance",
    }
