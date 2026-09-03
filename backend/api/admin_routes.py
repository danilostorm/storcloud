from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from activity_models import PlaySession
from database import get_db
from main import get_current_user
from models import Device, RomEntry, SaveState, User

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin required")
    return user


class StatusBody(BaseModel):
    active: bool


class RoleBody(BaseModel):
    role: str


@router.get("/overview")
def overview(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalar(select(func.count(User.id))) or 0
    active_users = db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    devices = db.scalar(select(func.count(Device.id)).where(Device.revoked_at.is_(None))) or 0
    roms = db.scalar(select(func.count(RomEntry.id))) or 0
    saves = db.scalar(select(func.count(SaveState.id))) or 0
    sessions = db.scalar(select(func.count(PlaySession.id))) or 0
    play_seconds = db.scalar(select(func.coalesce(func.sum(PlaySession.duration_seconds), 0))) or 0
    return {
        "users": int(users),
        "active_users": int(active_users),
        "devices": int(devices),
        "roms": int(roms),
        "saves": int(saves),
        "sessions": int(sessions),
        "play_seconds": int(play_seconds),
        "play_hours": round(int(play_seconds) / 3600, 1),
    }


@router.get("/users/detail")
def users_detail(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at.asc())).all()
    items = []
    for user in users:
        rom_count = db.scalar(select(func.count(RomEntry.id)).where(RomEntry.user_id == user.id)) or 0
        device_count = db.scalar(
            select(func.count(Device.id)).where(Device.user_id == user.id, Device.revoked_at.is_(None))
        ) or 0
        play_seconds = db.scalar(
            select(func.coalesce(func.sum(PlaySession.duration_seconds), 0)).where(PlaySession.user_id == user.id)
        ) or 0
        items.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "active": user.is_active,
            "created_at": user.created_at,
            "roms": int(rom_count),
            "devices": int(device_count),
            "play_seconds": int(play_seconds),
        })
    return {"items": items, "count": len(items)}


@router.put("/users/{user_id}/status")
def set_status(
    user_id: int,
    body: StatusBody,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    if user.id == admin.id and not body.active:
        raise HTTPException(status_code=400, detail="you cannot disable your own admin account")
    user.is_active = body.active
    db.commit()
    return {"ok": True, "user_id": user.id, "active": user.is_active}


@router.put("/users/{user_id}/role")
def set_role(
    user_id: int,
    body: RoleBody,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if body.role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="role must be admin or user")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    if user.role == "admin" and body.role != "admin":
        admins = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))) or 0
        if admins <= 1:
            raise HTTPException(status_code=400, detail="cannot demote the last active admin")
    user.role = body.role
    db.commit()
    return {"ok": True, "user_id": user.id, "role": user.role}


@router.get("/activity")
def recent_activity(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(PlaySession).order_by(PlaySession.last_seen_at.desc()).limit(100)).all()
    users = {u.id: u.username for u in db.scalars(select(User)).all()}
    return {
        "items": [
            {
                "id": row.id,
                "username": users.get(row.user_id, f"user-{row.user_id}"),
                "mode": row.mode,
                "title": row.title,
                "game_key": row.game_key,
                "platform_id": row.platform_id,
                "duration_seconds": row.duration_seconds,
                "started_at": row.started_at,
                "last_seen_at": row.last_seen_at,
                "ended_at": row.ended_at,
            }
            for row in rows
        ]
    }
