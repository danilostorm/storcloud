import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from activity_models import PlaySession
from database import get_db
from main import get_current_user
from models import User

router = APIRouter(prefix="/activity", tags=["activity"])
ALLOWED_MODES = {"retro-wasm", "browser-wasm", "local-native", "remote-stream"}


def utcnow():
    return datetime.now(timezone.utc)


class StartSessionBody(BaseModel):
    mode: str = Field(max_length=30)
    game_key: str = Field(min_length=1, max_length=140)
    title: str = Field(min_length=1, max_length=200)
    platform_id: str | None = Field(default=None, max_length=40)
    device_id: str | None = Field(default=None, max_length=36)


def session_dict(row: PlaySession) -> dict:
    active = row.ended_at is None and row.last_seen_at >= utcnow() - timedelta(minutes=2)
    return {
        "id": row.id,
        "mode": row.mode,
        "game_key": row.game_key,
        "title": row.title,
        "platform_id": row.platform_id,
        "device_id": row.device_id,
        "started_at": row.started_at,
        "last_seen_at": row.last_seen_at,
        "ended_at": row.ended_at,
        "duration_seconds": row.duration_seconds,
        "active": active,
    }


def calculate_duration(row: PlaySession, end: datetime) -> int:
    start = row.started_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return max(0, int((end - start).total_seconds()))


@router.post("/start")
def start_session(body: StartSessionBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail="unsupported execution mode")
    now = utcnow()
    row = PlaySession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        mode=body.mode,
        game_key=body.game_key,
        title=body.title.strip(),
        platform_id=body.platform_id,
        device_id=body.device_id,
        started_at=now,
        last_seen_at=now,
    )
    db.add(row)
    db.commit()
    return {"session": session_dict(row)}


@router.post("/{session_id}/heartbeat")
def heartbeat_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(PlaySession, session_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="play session not found")
    if row.ended_at is not None:
        return {"session": session_dict(row)}
    row.last_seen_at = utcnow()
    row.duration_seconds = calculate_duration(row, row.last_seen_at)
    db.commit()
    return {"session": session_dict(row)}


@router.post("/{session_id}/end")
def end_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(PlaySession, session_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="play session not found")
    if row.ended_at is None:
        now = utcnow()
        row.last_seen_at = now
        row.ended_at = now
        row.duration_seconds = calculate_duration(row, now)
        db.commit()
    return {"session": session_dict(row)}


@router.get("/recent")
def recent_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(PlaySession)
        .where(PlaySession.user_id == user.id)
        .order_by(PlaySession.started_at.desc())
        .limit(50)
    ).all()
    return {"items": [session_dict(row) for row in rows], "count": len(rows)}
