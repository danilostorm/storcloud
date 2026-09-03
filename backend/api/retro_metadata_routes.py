import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from library_routes import current_user
from models import RomEntry, User
from retro_metadata_models import RomMetadata

router = APIRouter(prefix="/library", tags=["retro-metadata"])
MEDIA_ROOT = Path(os.getenv("STORCLOUD_MEDIA_ROOT", "/storage/media"))
MAX_MEDIA_BYTES = 8 * 1024 * 1024

PLATFORM_NAMES = {
    "nes": ["Nintendo - Nintendo Entertainment System"],
    "snes": ["Nintendo - Super Nintendo Entertainment System"],
    "gb": ["Nintendo - Game Boy", "Nintendo - Game Boy Color"],
    "gba": ["Nintendo - Game Boy Advance"],
    "genesis": ["Sega - Mega Drive - Genesis"],
    "sms": ["Sega - Master System - Mark III"],
    "gamegear": ["Sega - Game Gear"],
    "arcade": ["FBNeo - Arcade Games", "MAME"],
    "n64": ["Nintendo - Nintendo 64"],
    "ps1": ["Sony - PlayStation"],
}

REGION_TAGS = re.compile(
    r"\s*[\[(](?:USA|Europe|World|Japan|Brazil|Asia|En|Es|Fr|De|It|Pt|Rev[^\])]*|Beta|Proto|Demo|Sample|Unl|Virtual Console|Switch Online|Disc[^\])]*)[\])]\s*$",
    re.IGNORECASE,
)
ANY_TRAILING_TAG = re.compile(r"\s*[\[(][^\])]{1,80}[\])]\s*$")
FORBIDDEN_THUMB_CHARS = re.compile(r'[&*/:`<>?\\|\"]')


def utcnow():
    return datetime.now(timezone.utc)


def get_rom(rom_id: str, user: User, db: Session) -> RomEntry:
    row = db.get(RomEntry, rom_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="ROM not found")
    return row


def clean_rom_name(name: str) -> str:
    stem = Path(name).stem.replace("_", " ").strip()
    previous = None
    while stem and previous != stem:
        previous = stem
        stem = REGION_TAGS.sub("", stem).strip()
    # GoodTools/no-intro filenames sometimes carry several generic tags. Remove
    # up to three trailing tags as a fallback, while keeping the original title
    # as another candidate.
    fallback = stem
    for _ in range(3):
        updated = ANY_TRAILING_TAG.sub("", fallback).strip()
        if updated == fallback:
            break
        fallback = updated
    stem = fallback or stem
    stem = re.sub(r"\s+", " ", stem).strip(" ._-")
    return stem


def candidate_names(row: RomEntry) -> list[str]:
    values = [row.title.strip(), clean_rom_name(row.file_name)]
    out = []
    seen = set()
    for value in values:
        if value and value.lower() not in seen:
            seen.add(value.lower())
            out.append(value)
    return out


def thumbnail_url(platform: str, media_type: str, name: str) -> str:
    safe_name = FORBIDDEN_THUMB_CHARS.sub("_", name) + ".png"
    directory = {"boxart": "Named_Boxarts", "snap": "Named_Snaps", "title": "Named_Titles"}[media_type]
    return "https://thumbnails.libretro.com/{}/{}/{}".format(
        quote(platform, safe=""),
        directory,
        quote(safe_name, safe=""),
    )


def download_image(url: str, target: Path) -> bool:
    request = Request(url, headers={"User-Agent": "StorCloud/0.9 cover-scanner", "Accept": "image/*"})
    try:
        with urlopen(request, timeout=8) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if not content_type.startswith("image/"):
                return False
            data = response.read(MAX_MEDIA_BYTES + 1)
            if not data or len(data) > MAX_MEDIA_BYTES:
                return False
    except Exception:
        return False

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(target)
    return True


def metadata_dict(row: RomMetadata | None, rom_id: str) -> dict:
    if not row:
        return {
            "rom_id": rom_id,
            "matched_name": None,
            "source": None,
            "description": None,
            "developer": None,
            "publisher": None,
            "release_date": None,
            "genres": [],
            "cover_url": None,
            "background_url": None,
            "scanned_at": None,
        }
    return {
        "rom_id": rom_id,
        "matched_name": row.matched_name,
        "source": row.source,
        "description": row.description,
        "developer": row.developer,
        "publisher": row.publisher,
        "release_date": row.release_date,
        "genres": [x for x in (row.genres or "").split("|") if x],
        "cover_url": f"/api/library/roms/{rom_id}/cover" if row.cover_path else None,
        "background_url": f"/api/library/roms/{rom_id}/background" if row.background_path else None,
        "scanned_at": row.scanned_at,
    }


@router.get("/roms/{rom_id}/metadata")
def get_metadata(rom_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_rom(rom_id, user, db)
    return {"metadata": metadata_dict(db.get(RomMetadata, rom_id), rom_id)}


@router.post("/roms/{rom_id}/scan")
def scan_metadata(rom_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    rom = get_rom(rom_id, user, db)
    metadata = db.get(RomMetadata, rom_id) or RomMetadata(rom_id=rom_id)
    media_dir = MEDIA_ROOT / str(user.id) / rom_id
    cover_target = media_dir / "boxart.png"
    background_target = media_dir / "snap.png"

    platform_names = PLATFORM_NAMES.get(rom.platform_id, [])
    if rom.platform_id == "gb" and rom.file_name.lower().endswith(".gbc"):
        platform_names = ["Nintendo - Game Boy Color", "Nintendo - Game Boy"]

    matched_name = None
    matched_platform = None
    for platform_name in platform_names:
        for name in candidate_names(rom):
            if download_image(thumbnail_url(platform_name, "boxart", name), cover_target):
                matched_name = name
                matched_platform = platform_name
                break
        if matched_name:
            break

    if matched_name and matched_platform:
        # Snap is optional. A missing screenshot must never make a valid cover fail.
        download_image(thumbnail_url(matched_platform, "snap", matched_name), background_target)
        metadata.matched_name = matched_name
        metadata.source = "libretro-thumbnails"
        metadata.cover_path = str(cover_target)
        metadata.background_path = str(background_target) if background_target.is_file() else None
        # Prefer the matched canonical-ish filename when the user did not provide a custom title.
        if clean_rom_name(rom.file_name).lower() == rom.title.lower() or rom.title == Path(rom.file_name).stem:
            rom.title = matched_name[:180]
    else:
        metadata.matched_name = None
        metadata.source = "libretro-thumbnails-no-match"
        if cover_target.exists():
            cover_target.unlink(missing_ok=True)
        if background_target.exists():
            background_target.unlink(missing_ok=True)
        metadata.cover_path = None
        metadata.background_path = None

    metadata.scanned_at = utcnow()
    db.add(metadata)
    db.commit()
    db.refresh(metadata)
    return {
        "matched": bool(matched_name),
        "metadata": metadata_dict(metadata, rom_id),
        "candidates": candidate_names(rom),
    }


@router.post("/scan")
def scan_library(user: User = Depends(current_user), db: Session = Depends(get_db)):
    roms = db.scalars(select(RomEntry).where(RomEntry.user_id == user.id).order_by(RomEntry.created_at.desc())).all()
    return {
        "queued": len(roms),
        "items": [
            {"id": rom.id, "title": rom.title, "scan_url": f"/api/library/roms/{rom.id}/scan"}
            for rom in roms
        ],
        "mode": "client-batched",
    }


@router.get("/roms/{rom_id}/cover")
def get_cover(rom_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_rom(rom_id, user, db)
    metadata = db.get(RomMetadata, rom_id)
    if not metadata or not metadata.cover_path or not Path(metadata.cover_path).is_file():
        raise HTTPException(status_code=404, detail="cover not found")
    return FileResponse(metadata.cover_path)


@router.get("/roms/{rom_id}/background")
def get_background(rom_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    get_rom(rom_id, user, db)
    metadata = db.get(RomMetadata, rom_id)
    if not metadata or not metadata.background_path or not Path(metadata.background_path).is_file():
        raise HTTPException(status_code=404, detail="background not found")
    return FileResponse(metadata.background_path)


@router.post("/roms/{rom_id}/cover")
async def upload_cover(
    rom_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    get_rom(rom_id, user, db)
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=400, detail="cover must be PNG, JPEG or WebP")
    data = await file.read(MAX_MEDIA_BYTES + 1)
    if not data or len(data) > MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="cover is too large")
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[content_type]
    media_dir = MEDIA_ROOT / str(user.id) / rom_id
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / f"custom-cover{extension}"
    target.write_bytes(data)

    metadata = db.get(RomMetadata, rom_id) or RomMetadata(rom_id=rom_id)
    metadata.cover_path = str(target)
    metadata.source = "custom"
    metadata.scanned_at = utcnow()
    db.add(metadata)
    db.commit()
    db.refresh(metadata)
    return {"metadata": metadata_dict(metadata, rom_id)}
