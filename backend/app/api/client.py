"""Pseudonymous client presence and release telemetry."""
import hashlib
import hmac
import re
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import SECRET_KEY, get_current_user
from app.database import get_db
from app.models import ActiveClient, ClientActivity, User

router = APIRouter()


class Heartbeat(BaseModel):
    platform: str
    app_version: str
    client_id: str | None = None


@router.post("/heartbeat")
def heartbeat(payload: Heartbeat, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.platform not in {"ios", "android", "web"}:
        raise HTTPException(422, "Nền tảng không hợp lệ.")
    if not re.fullmatch(r"[a-zA-Z0-9.+_-]{1,40}", payload.app_version):
        raise HTTPException(422, "Phiên bản không hợp lệ.")
    record_version_event = payload.client_id is None
    if payload.client_id is not None:
        try:
            normalized_id = uuid.UUID(payload.client_id).hex
        except (ValueError, AttributeError):
            raise HTTPException(422, "Mã phiên thiết bị không hợp lệ.")
        key = hmac.new(SECRET_KEY.encode(), normalized_id.encode(), hashlib.sha256).hexdigest()
        presence = db.get(ActiveClient, key)
        if presence is None:
            record_version_event = True
            presence = ActiveClient(key=key, user_id=user.id,
                                    platform=payload.platform,
                                    app_version=payload.app_version)
            db.add(presence)
        elif presence.app_version != payload.app_version:
            record_version_event = True
        presence.user_id = user.id
        presence.platform = payload.platform
        presence.app_version = payload.app_version
        presence.last_seen = datetime.utcnow()
    if record_version_event:
        db.add(ClientActivity(user_id=user.id, platform=payload.platform,
                              app_version=payload.app_version, event="heartbeat"))
    db.commit()
    return {"success": True}
