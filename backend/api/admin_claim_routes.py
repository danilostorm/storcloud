import hmac
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from library_routes import current_user
from models import User

router = APIRouter(prefix="/setup", tags=["setup"])
SETUP_TOKEN = os.getenv("STORCLOUD_SETUP_TOKEN", "")


class ClaimAdminBody(BaseModel):
    setup_token: str = Field(min_length=1, max_length=300)


@router.get("/admin-status")
def admin_status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    admin_count = db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
    return {
        "current_role": user.role,
        "admin_exists": admin_count > 0,
        "can_claim": user.role != "admin" and admin_count == 0 and bool(SETUP_TOKEN),
    }


@router.post("/claim-admin")
def claim_admin(
    body: ClaimAdminBody,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role == "admin":
        return {"ok": True, "role": "admin", "already_admin": True}

    admin_count = db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
    if admin_count > 0:
        raise HTTPException(status_code=409, detail="an administrator already exists")
    if not SETUP_TOKEN or not hmac.compare_digest(body.setup_token, SETUP_TOKEN):
        raise HTTPException(status_code=403, detail="invalid setup token")

    user.role = "admin"
    db.commit()
    db.refresh(user)
    return {"ok": True, "role": user.role, "username": user.username}
