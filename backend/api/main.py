import hashlib
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Device, DevicePairTicket, LaunchTicket, SaveState, User, UserSession
from security import hash_password, new_token, token_hash, verify_password

APP_VERSION = "0.6.0"
SESSION_COOKIE = "storcloud_session"
SESSION_DAYS = int(os.getenv("STORCLOUD_SESSION_DAYS", "30"))
COOKIE_SECURE = os.getenv("STORCLOUD_COOKIE_SECURE", "false").lower() == "true"
ALLOW_REGISTRATION = os.getenv("STORCLOUD_ALLOW_REGISTRATION", "true").lower() == "true"
SETUP_TOKEN = os.getenv("STORCLOUD_SETUP_TOKEN", "")
SAVE_ROOT = Path(os.getenv("STORCLOUD_SAVE_ROOT", "/storage/saves"))
MAX_SAVE_BYTES = int(os.getenv("STORCLOUD_MAX_SAVE_BYTES", str(64 * 1024 * 1024)))
RUNTIME_GAMES = Path("/runtime/games")
SAFE_KEY = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
SAFE_SLOT = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    SAVE_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="StorCloud API", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=10, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    setup_token: str | None = None


class LoginBody(BaseModel):
    username: str
    password: str


class PairAgentBody(BaseModel):
    ticket: str
    name: str = Field(min_length=1, max_length=100)
    os: str = Field(min_length=1, max_length=50)
    arch: str = Field(min_length=1, max_length=50)
    logical_cpus: int = Field(default=1, ge=1, le=1024)


class LaunchTicketBody(BaseModel):
    game_id: str = Field(min_length=1, max_length=100)


class ConsumeLaunchBody(BaseModel):
    ticket: str
    game_id: str = Field(min_length=1, max_length=100)


RETRO_PLATFORMS = [
    {"id": "nes", "name": "Nintendo Entertainment System", "short": "NES", "core": "fceumm", "extensions": ["nes"]},
    {"id": "snes", "name": "Super Nintendo / Super Famicom", "short": "SNES", "core": "snes9x", "extensions": ["sfc", "smc"]},
    {"id": "gb", "name": "Game Boy / Game Boy Color", "short": "GB / GBC", "core": "mgba", "extensions": ["gb", "gbc"]},
    {"id": "gba", "name": "Game Boy Advance", "short": "GBA", "core": "mgba", "extensions": ["gba"]},
    {"id": "genesis", "name": "Mega Drive / Genesis", "short": "Mega Drive", "core": "genesis_plus_gx", "extensions": ["md", "gen"]},
    {"id": "sms", "name": "Master System", "short": "Master System", "core": "genesis_plus_gx", "extensions": ["sms"]},
    {"id": "gamegear", "name": "Game Gear", "short": "Game Gear", "core": "genesis_plus_gx", "extensions": ["gg"]},
    {"id": "arcade", "name": "Arcade / Neo Geo", "short": "Arcade", "core": "fbneo", "extensions": ["zip"]},
    {"id": "n64", "name": "Nintendo 64", "short": "N64", "core": "mupen64plus_next", "extensions": ["z64", "n64", "v64"], "experimental": True},
    {"id": "ps1", "name": "PlayStation", "short": "PS1", "core": "pcsx_rearmed", "extensions": ["chd"], "experimental": True},
]


def installed(game_id: str) -> bool:
    return (RUNTIME_GAMES / game_id / "index.html").is_file()


def user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at,
    }


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="authentication required")
    row = db.get(UserSession, token_hash(raw))
    if not row or row.expires_at <= utcnow():
        if row:
            db.delete(row)
            db.commit()
        raise HTTPException(status_code=401, detail="session expired")
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="account unavailable")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin required")
    return user


def create_session(db: Session, user: User, response: Response):
    raw = new_token(32)
    db.add(
        UserSession(
            token_hash=token_hash(raw),
            user_id=user.id,
            expires_at=utcnow() + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        raw,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def bearer_device(authorization: str | None, db: Session) -> Device:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="device authentication required")
    raw = authorization[7:].strip()
    device = db.scalar(select(Device).where(Device.token_hash == token_hash(raw)))
    if not device or device.revoked_at is not None:
        raise HTTPException(status_code=401, detail="device revoked or unknown")
    return device


def validate_key(value: str, regex: re.Pattern, label: str) -> str:
    if not regex.fullmatch(value):
        raise HTTPException(status_code=400, detail=f"invalid {label}")
    return value


def game_catalog():
    return [
        {
            "id": "doom-wasm",
            "name": "Doom / FreeDoom WASM",
            "type": "wasm",
            "engine": "Chocolate Doom + Emscripten",
            "rendering": "client",
            "status": "ready" if installed("doom-wasm") else "installing",
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
            "description": "Uma biblioteca e um player únicos, com cloud saves opcionais por conta.",
        },
        {
            "id": "pc-local",
            "name": "PC Local",
            "type": "local",
            "engine": "StorCloud Local Agent",
            "rendering": "client-native",
            "status": "alpha",
            "launch_url": "/pc/",
            "description": "Jogos Windows/Linux executados no computador do jogador com pairing, allowlist e tickets de lançamento.",
        },
        {
            "id": "pc-wasm",
            "name": "PC WebAssembly",
            "type": "wasm",
            "engine": "WASM / WebGL / WebGPU",
            "rendering": "client",
            "status": "research",
            "launch_url": None,
            "description": "Ports reais de jogos/engines PC para WebAssembly rodam 100% no navegador quando compatíveis.",
        },
        {
            "id": "remote-stream",
            "name": "Streaming Fallback",
            "type": "stream",
            "engine": "Wolf / Sunshine compatible",
            "rendering": "server-or-host",
            "status": "planned",
            "launch_url": None,
            "description": "Último recurso para títulos sem rota de execução local.",
        },
    ]


@app.get("/")
def root():
    return {
        "name": "StorCloud",
        "version": APP_VERSION,
        "status": "online",
        "modes": ["browser-wasm", "retro-wasm", "local-native", "remote-stream"],
        "strategy": "local-first",
    }


@app.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    db.scalar(select(func.count(User.id)))
    return {"ok": True, "database": "online", "version": APP_VERSION}


@app.get("/setup/status")
def setup_status(db: Session = Depends(get_db)):
    users = db.scalar(select(func.count(User.id))) or 0
    return {"initialized": users > 0, "registration_open": ALLOW_REGISTRATION, "version": APP_VERSION}


@app.post("/auth/register")
def register(body: RegisterBody, response: Response, db: Session = Depends(get_db)):
    username = body.username.strip().lower()
    email = body.email.strip().lower() if body.email else None
    if not re.fullmatch(r"[a-z0-9_.-]{3,50}", username):
        raise HTTPException(status_code=400, detail="username must use letters, numbers, ., _ or -")

    user_count = db.scalar(select(func.count(User.id))) or 0
    if user_count == 0:
        if not SETUP_TOKEN or body.setup_token != SETUP_TOKEN:
            raise HTTPException(status_code=403, detail="valid setup token required for first admin")
        role = "admin"
    else:
        if not ALLOW_REGISTRATION:
            raise HTTPException(status_code=403, detail="registration is closed")
        role = "user"

    user = User(username=username, email=email, password_hash=hash_password(body.password), role=role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="username or email already exists")
    db.refresh(user)
    create_session(db, user, response)
    return {"user": user_dict(user), "first_admin": role == "admin"}


@app.post("/auth/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    username = body.username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    create_session(db, user, response)
    return {"user": user_dict(user)}


@app.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        db.execute(delete(UserSession).where(UserSession.token_hash == token_hash(raw)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"user": user_dict(user)}


@app.get("/admin/users")
def admin_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at.asc())).all()
    return {"items": [user_dict(user) for user in users], "count": len(users)}


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


@app.get("/devices")
def list_devices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    devices = db.scalars(select(Device).where(Device.user_id == user.id).order_by(Device.created_at.desc())).all()
    return {
        "items": [
            {
                "id": d.id,
                "name": d.name,
                "os": d.os,
                "arch": d.arch,
                "logical_cpus": d.logical_cpus,
                "paired_at": d.paired_at,
                "last_seen_at": d.last_seen_at,
                "revoked": d.revoked_at is not None,
            }
            for d in devices
        ]
    }


@app.post("/devices/pair-ticket")
def create_pair_ticket(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw = new_token(24)
    expires = utcnow() + timedelta(minutes=10)
    db.add(DevicePairTicket(token_hash=token_hash(raw), user_id=user.id, expires_at=expires))
    db.commit()
    return {"ticket": raw, "expires_at": expires}


@app.delete("/devices/{device_id}")
def revoke_device(device_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device or device.user_id != user.id:
        raise HTTPException(status_code=404, detail="device not found")
    device.revoked_at = utcnow()
    db.commit()
    return {"ok": True}


@app.post("/devices/{device_id}/launch-ticket")
def create_launch_ticket(
    device_id: str,
    body: LaunchTicketBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.get(Device, device_id)
    if not device or device.user_id != user.id or device.revoked_at is not None:
        raise HTTPException(status_code=404, detail="active device not found")
    raw = new_token(24)
    expires = utcnow() + timedelta(seconds=45)
    db.add(
        LaunchTicket(
            token_hash=token_hash(raw),
            user_id=user.id,
            device_id=device.id,
            game_id=body.game_id,
            expires_at=expires,
        )
    )
    db.commit()
    return {"ticket": raw, "expires_at": expires, "device_id": device.id, "game_id": body.game_id}


@app.post("/agent/pair")
def agent_pair(body: PairAgentBody, db: Session = Depends(get_db)):
    row = db.get(DevicePairTicket, token_hash(body.ticket))
    if not row or row.consumed_at is not None or row.expires_at <= utcnow():
        raise HTTPException(status_code=401, detail="invalid or expired pairing ticket")
    raw_device_token = new_token(32)
    device = Device(
        id=str(uuid.uuid4()),
        user_id=row.user_id,
        name=body.name,
        os=body.os,
        arch=body.arch,
        logical_cpus=body.logical_cpus,
        token_hash=token_hash(raw_device_token),
        last_seen_at=utcnow(),
    )
    row.consumed_at = utcnow()
    db.add(device)
    db.commit()
    return {"device_id": device.id, "device_token": raw_device_token, "paired": True}


@app.post("/agent/heartbeat")
def agent_heartbeat(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    device = bearer_device(authorization, db)
    device.last_seen_at = utcnow()
    db.commit()
    return {"ok": True, "device_id": device.id, "server_time": utcnow()}


@app.post("/agent/launch/consume")
def consume_launch_ticket(
    body: ConsumeLaunchBody,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = bearer_device(authorization, db)
    ticket = db.get(LaunchTicket, token_hash(body.ticket))
    if (
        not ticket
        or ticket.device_id != device.id
        or ticket.game_id != body.game_id
        or ticket.consumed_at is not None
        or ticket.expires_at <= utcnow()
    ):
        raise HTTPException(status_code=401, detail="invalid or expired launch ticket")
    ticket.consumed_at = utcnow()
    device.last_seen_at = utcnow()
    db.commit()
    return {"ok": True, "game_id": body.game_id, "device_id": device.id}


@app.get("/saves")
def list_saves(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(SaveState).where(SaveState.user_id == user.id).order_by(SaveState.updated_at.desc())).all()
    return {
        "items": [
            {
                "id": row.id,
                "game_key": row.game_key,
                "slot": row.slot,
                "original_name": row.original_name,
                "size_bytes": row.size_bytes,
                "sha256": row.sha256,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    }


@app.post("/saves/{game_key}/{slot}")
async def upload_save(
    game_key: str,
    slot: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game_key = validate_key(game_key, SAFE_KEY, "game key")
    slot = validate_key(slot, SAFE_SLOT, "slot")
    target_dir = SAVE_ROOT / str(user.id) / game_key
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{slot}.state"
    temp = target.with_suffix(".tmp")
    digest = hashlib.sha256()
    total = 0
    try:
        with temp.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_SAVE_BYTES:
                    raise HTTPException(status_code=413, detail="save state too large")
                digest.update(chunk)
                output.write(chunk)
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)

    row = db.scalar(
        select(SaveState).where(
            SaveState.user_id == user.id,
            SaveState.game_key == game_key,
            SaveState.slot == slot,
        )
    )
    now = utcnow()
    if row:
        row.original_name = file.filename or f"{game_key}.state"
        row.storage_path = str(target)
        row.size_bytes = total
        row.sha256 = digest.hexdigest()
        row.updated_at = now
    else:
        row = SaveState(
            id=str(uuid.uuid4()),
            user_id=user.id,
            game_key=game_key,
            slot=slot,
            original_name=file.filename or f"{game_key}.state",
            storage_path=str(target),
            size_bytes=total,
            sha256=digest.hexdigest(),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    return {"ok": True, "game_key": game_key, "slot": slot, "size_bytes": total, "sha256": digest.hexdigest()}


@app.get("/saves/{game_key}/{slot}")
def download_save(
    game_key: str,
    slot: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game_key = validate_key(game_key, SAFE_KEY, "game key")
    slot = validate_key(slot, SAFE_SLOT, "slot")
    row = db.scalar(
        select(SaveState).where(
            SaveState.user_id == user.id,
            SaveState.game_key == game_key,
            SaveState.slot == slot,
        )
    )
    if not row or not Path(row.storage_path).is_file():
        raise HTTPException(status_code=404, detail="save not found")
    return FileResponse(row.storage_path, media_type="application/octet-stream", filename=row.original_name)


@app.delete("/saves/{game_key}/{slot}")
def delete_save(
    game_key: str,
    slot: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    game_key = validate_key(game_key, SAFE_KEY, "game key")
    slot = validate_key(slot, SAFE_SLOT, "slot")
    row = db.scalar(
        select(SaveState).where(
            SaveState.user_id == user.id,
            SaveState.game_key == game_key,
            SaveState.slot == slot,
        )
    )
    if not row:
        raise HTTPException(status_code=404, detail="save not found")
    Path(row.storage_path).unlink(missing_ok=True)
    db.delete(row)
    db.commit()
    return {"ok": True}


@app.get("/capabilities")
def capabilities():
    return {
        "wasm": True,
        "webgl": True,
        "webgpu": "client-detected",
        "retro_emulation": "client",
        "multiuser": True,
        "cloud_saves": True,
        "local_agent": "alpha-pairing",
        "signed_launch_tickets": True,
        "remote_streaming": "planned",
        "server_gpu_required_for_wasm": False,
    }
