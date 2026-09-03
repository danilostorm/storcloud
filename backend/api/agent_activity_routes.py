import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from activity_models import PlaySession
from database import get_db
from main import bearer_device

router = APIRouter(prefix="/agent/activity", tags=["agent-activity"])


def utcnow():
    return datetime.now(timezone.utc)


class AgentPlayStart(BaseModel):
    game_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)


@router.post("/start")
def start_local_session(
    body: AgentPlayStart,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = bearer_device(authorization, db)
    now = utcnow()
    row = PlaySession(
        id=str(uuid.uuid4()),
        user_id=device.user_id,
        mode="local-native",
        game_key=body.game_id,
        title=body.title.strip(),
        device_id=device.id,
        started_at=now,
        last_seen_at=now,
    )
    db.add(row)
    db.commit()
    return {"session_id": row.id}


@router.post("/{session_id}/heartbeat")
def heartbeat_local_session(
    session_id: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = bearer_device(authorization, db)
    row = db.get(PlaySession, session_id)
    if not row or row.device_id != device.id or row.user_id != device.user_id:
        raise HTTPException(status_code=404, detail="play session not found")
    if row.ended_at is None:
        now = utcnow()
        row.last_seen_at = now
        started = row.started_at if row.started_at.tzinfo else row.started_at.replace(tzinfo=timezone.utc)
        row.duration_seconds = max(0, int((now - started).total_seconds()))
        db.commit()
    return {"ok": True}


@router.post("/{session_id}/end")
def end_local_session(
    session_id: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = bearer_device(authorization, db)
    row = db.get(PlaySession, session_id)
    if not row or row.device_id != device.id or row.user_id != device.user_id:
        raise HTTPException(status_code=404, detail="play session not found")
    if row.ended_at is None:
        now = utcnow()
        row.last_seen_at = now
        row.ended_at = now
        started = row.started_at if row.started_at.tzinfo else row.started_at.replace(tzinfo=timezone.utc)
        row.duration_seconds = max(0, int((now - started).total_seconds()))
        db.commit()
    return {"ok": True, "duration_seconds": row.duration_seconds}
