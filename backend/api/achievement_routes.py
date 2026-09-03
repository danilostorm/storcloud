from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from achievement_models import AchievementUnlock
from activity_models import PlaySession
from database import get_db
from main import get_current_user
from models import Device, RomEntry, User

router = APIRouter(prefix="/achievements", tags=["achievements"])

ACHIEVEMENTS = [
    {
        "id": "first-launch",
        "title": "Primeiro Boot",
        "description": "Inicie sua primeira sessão no StorCloud.",
        "icon": "▶",
    },
    {
        "id": "one-hour",
        "title": "Uma Hora na Nuvem",
        "description": "Some pelo menos 1 hora de jogo registrada.",
        "icon": "⏱",
    },
    {
        "id": "retro-collector",
        "title": "Colecionador Retro",
        "description": "Adicione 5 jogos à sua biblioteca pessoal.",
        "icon": "🕹",
    },
    {
        "id": "multi-system",
        "title": "Explorador de Sistemas",
        "description": "Jogue em pelo menos 3 plataformas retro diferentes.",
        "icon": "🎮",
    },
    {
        "id": "local-pc",
        "title": "Potência Local",
        "description": "Inicie um jogo pelo StorCloud Local Agent.",
        "icon": "⚡",
    },
    {
        "id": "paired-device",
        "title": "Máquina Pareada",
        "description": "Pareie seu primeiro PC com a conta.",
        "icon": "🖥",
    },
]


def evaluate(user_id: int, db: Session) -> set[str]:
    unlocked: set[str] = set()

    session_count = db.scalar(select(func.count(PlaySession.id)).where(PlaySession.user_id == user_id)) or 0
    if session_count >= 1:
        unlocked.add("first-launch")

    total_seconds = db.scalar(
        select(func.coalesce(func.sum(PlaySession.duration_seconds), 0)).where(PlaySession.user_id == user_id)
    ) or 0
    if int(total_seconds) >= 3600:
        unlocked.add("one-hour")

    rom_count = db.scalar(select(func.count(RomEntry.id)).where(RomEntry.user_id == user_id)) or 0
    if rom_count >= 5:
        unlocked.add("retro-collector")

    platform_count = db.scalar(
        select(func.count(func.distinct(PlaySession.platform_id))).where(
            PlaySession.user_id == user_id,
            PlaySession.platform_id.is_not(None),
        )
    ) or 0
    if platform_count >= 3:
        unlocked.add("multi-system")

    local_count = db.scalar(
        select(func.count(PlaySession.id)).where(
            PlaySession.user_id == user_id,
            PlaySession.mode == "local-native",
        )
    ) or 0
    if local_count >= 1:
        unlocked.add("local-pc")

    device_count = db.scalar(
        select(func.count(Device.id)).where(Device.user_id == user_id, Device.revoked_at.is_(None))
    ) or 0
    if device_count >= 1:
        unlocked.add("paired-device")

    existing = {
        row.achievement_id
        for row in db.scalars(select(AchievementUnlock).where(AchievementUnlock.user_id == user_id)).all()
    }
    for achievement_id in unlocked - existing:
        db.add(AchievementUnlock(user_id=user_id, achievement_id=achievement_id))
    if unlocked - existing:
        db.commit()
    return unlocked | existing


@router.get("")
def list_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    unlocked = evaluate(user.id, db)
    rows = {
        row.achievement_id: row
        for row in db.scalars(select(AchievementUnlock).where(AchievementUnlock.user_id == user.id)).all()
    }
    items = []
    for item in ACHIEVEMENTS:
        row = rows.get(item["id"])
        items.append({
            **item,
            "unlocked": item["id"] in unlocked,
            "unlocked_at": row.unlocked_at if row else None,
        })
    return {
        "items": items,
        "unlocked": sum(1 for item in items if item["unlocked"]),
        "total": len(items),
    }
