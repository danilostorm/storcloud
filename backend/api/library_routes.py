import hashlib
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import RomEntry, User, UserSession
from retro_metadata_models import RomMetadata
from security import token_hash

router = APIRouter(prefix="/library", tags=["library"])
SESSION_COOKIE = "storcloud_session"
ROM_ROOT = Path(os.getenv("STORCLOUD_ROM_ROOT", "/storage/roms"))
MEDIA_ROOT = Path(os.getenv("STORCLOUD_MEDIA_ROOT", "/storage/media"))
MAX_ROM_BYTES = int(os.getenv("STORCLOUD_MAX_ROM_BYTES", str(2 * 1024 * 1024 * 1024)))
SAFE_PLATFORM = re.compile(r"^[a-z0-9_-]{1,40}$")

PLATFORMS = {
    "nes": {"extensions": {"nes"}},
    "snes": {"extensions": {"sfc", "smc"}},
    "gb": {"extensions": {"gb", "gbc"}},
    "gba": {"extensions": {"gba"}},
    "genesis": {"extensions": {"md", "gen"}},
    "sms": {"extensions": {"sms"}},
    "gamegear": {"extensions": {"gg"}},
    "arcade": {"extensions": {"zip"}},
    "n64": {"extensions": {"z64", "n64", "v64"}},
    "ps1": {"extensions": {"chd"}},
}


def utcnow():
    return datetime.now(timezone.utc)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="authentication required")
    session = db.get(UserSession, token_hash(raw))
    if not session or session.expires_at <= utcnow():
        raise HTTPException(status_code=401, detail="session expired")
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="account unavailable")
    return user


def rom_dict(row: RomEntry, metadata: RomMetadata | None = None) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "platform_id": row.platform_id,
        "file_name": row.file_name,
        "size_bytes": row.size_bytes,
        "sha256": row.sha256,
        "favorite": row.favorite,
        "created_at": row.created_at,
        "last_played_at": row.last_played_at,
        "file_url": f"/api/library/roms/{row.id}/file",
        "cover_url": f"/api/library/roms/{row.id}/cover" if metadata and metadata.cover_path else None,
        "background_url": f"/api/library/roms/{row.id}/background" if metadata and metadata.background_path else None,
        "metadata_source": metadata.source if metadata else None,
        "matched_name": metadata.matched_name if metadata else None,
        "scanned_at": metadata.scanned_at if metadata else None,
    }


@router.get("/roms")
def list_roms(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(RomEntry)
        .where(RomEntry.user_id == user.id)
        .order_by(RomEntry.favorite.desc(), RomEntry.last_played_at.desc().nullslast(), RomEntry.title.asc())
    ).all()
    metadata_rows = db.scalars(select(RomMetadata).where(RomMetadata.rom_id.in_([row.id for row in rows]))).all() if rows else []
    metadata_map = {item.rom_id: item for item in metadata_rows}
    return {"items": [rom_dict(row, metadata_map.get(row.id)) for row in rows], "count": len(rows)}


@router.post("/roms")
async def upload_rom(
    platform_id: str = Form(...),
    title: str | None = Form(default=None),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    platform_id = platform_id.strip().lower()
    if not SAFE_PLATFORM.fullmatch(platform_id) or platform_id not in PLATFORMS:
        raise HTTPException(status_code=400, detail="unsupported platform")

    original_name = (file.filename or "game.rom").strip()
    extension = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if extension not in PLATFORMS[platform_id]["extensions"]:
        raise HTTPException(status_code=400, detail=f"file extension .{extension or '?'} does not match platform {platform_id}")

    rom_id = str(uuid.uuid4())
    target_dir = ROM_ROOT / str(user.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{rom_id}.{extension}"
    temp = target.with_suffix(target.suffix + ".tmp")
    digest = hashlib.sha256()
    total = 0

    try:
        with temp.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_ROM_BYTES:
                    raise HTTPException(status_code=413, detail="ROM is larger than server limit")
                digest.update(chunk)
                output.write(chunk)
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)

    display_title = (title or Path(original_name).stem).strip()[:180] or "Untitled game"
    row = RomEntry(
        id=rom_id,
        user_id=user.id,
        title=display_title,
        platform_id=platform_id,
        file_name=original_name,
        storage_path=str(target),
        size_bytes=total,
        sha256=digest.hexdigest(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="this ROM already exists in your library")
    db.refresh(row)
    return {"item": rom_dict(row), "auto_scan_url": f"/api/library/roms/{row.id}/scan"}


@router.get("/roms/{rom_id}/file")
def get_rom_file(rom_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(RomEntry, rom_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="ROM not found")
    path = Path(row.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="ROM file missing from storage")
    return FileResponse(path, media_type="application/octet-stream", filename=row.file_name)


@router.post("/roms/{rom_id}/played")
def mark_played(rom_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(RomEntry, rom_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="ROM not found")
    row.last_played_at = utcnow()
    db.commit()
    return {"ok": True, "last_played_at": row.last_played_at}


@router.put("/roms/{rom_id}/favorite")
def set_favorite(rom_id: str, value: bool, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(RomEntry, rom_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="ROM not found")
    row.favorite = value
    db.commit()
    return {"ok": True, "favorite": row.favorite}


@router.delete("/roms/{rom_id}")
def delete_rom(rom_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(RomEntry, rom_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="ROM not found")
    Path(row.storage_path).unlink(missing_ok=True)
    media_dir = MEDIA_ROOT / str(user.id) / rom_id
    if media_dir.exists():
        shutil.rmtree(media_dir, ignore_errors=True)
    db.delete(row)
    db.commit()
    return {"ok": True}
