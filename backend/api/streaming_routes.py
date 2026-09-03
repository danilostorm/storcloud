import json
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException

from main import get_current_user
from models import User

router = APIRouter(prefix="/streaming", tags=["streaming"])
CATALOG_PATH = Path(os.getenv("STORCLOUD_CATALOG_PATH", "/catalog/games.json"))


def bool_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def settings() -> dict:
    provider = os.getenv("STORCLOUD_STREAMING_PROVIDER", "sunshine").lower().strip()
    if provider not in {"wolf", "sunshine"}:
        provider = "sunshine"
    return {
        "enabled": bool_env("STORCLOUD_STREAMING_ENABLED"),
        "provider": provider,
        "host": os.getenv("STORCLOUD_STREAMING_HOST", "").strip(),
        "gateway_template": os.getenv("STORCLOUD_STREAMING_GATEWAY_TEMPLATE", "").strip(),
    }


def stream_app_for(game_id: str) -> str | None:
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    game = next((item for item in catalog.get("games", []) if item.get("id") == game_id), None)
    if not game:
        return None
    route = next((r for r in game.get("routes", []) if r.get("mode") == "remote-stream"), None)
    return route.get("stream_app_id") if route else None


@router.get("/status")
def streaming_status():
    config = settings()
    configured = config["enabled"] and bool(config["host"])
    return {
        "enabled": config["enabled"],
        "configured": configured,
        "provider": config["provider"],
        "host_configured": bool(config["host"]),
        "gateway_configured": bool(config["gateway_template"]),
        "transport": "moonlight-compatible",
        "browser_embedded": False,
        "note": "Wolf/Sunshine provide Moonlight-compatible streaming. Browser embedding requires a separate compatible web gateway/client.",
    }


@router.get("/{game_id}/descriptor")
def streaming_descriptor(game_id: str, _: User = Depends(get_current_user)):
    config = settings()
    app_id = stream_app_for(game_id)
    if not app_id:
        raise HTTPException(status_code=404, detail="no remote-stream route for this game")
    if not config["enabled"] or not config["host"]:
        raise HTTPException(status_code=503, detail="streaming fallback is not configured")

    launch_url = None
    if config["gateway_template"]:
        launch_url = (
            config["gateway_template"]
            .replace("{host}", quote(config["host"], safe=""))
            .replace("{app_id}", quote(app_id, safe=""))
            .replace("{provider}", quote(config["provider"], safe=""))
        )

    return {
        "game_id": game_id,
        "app_id": app_id,
        "provider": config["provider"],
        "host": config["host"],
        "transport": "moonlight-compatible",
        "launch_url": launch_url,
        "handoff": "configured-gateway" if launch_url else "moonlight-client-required",
    }
