"""Staff workspace: seven-class content, roles, diagnostics and mobile activity."""
import json
import re
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from firebase_admin import auth as firebase_auth

from app.api.auth import FIREBASE_ADMIN_READY, get_current_user
from app.api.inference_monitor import monitor
from app.api.disease_library import load_disease_library
from app.database import get_db
from app.models import ActiveClient, AdminAudit, ClientActivity, Diagnosis, DiseaseContent, User

router = APIRouter()
PRESENCE_WINDOW_SECONDS = 120
EDITABLE_FIELDS = ("overview", "symptoms", "favorable_conditions", "prevention", "ipm_advice")


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"admin", "employee"}:
        raise HTTPException(403, "Chỉ nhân viên được truy cập khu vực quản trị.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Chỉ quản trị viên được thực hiện thao tác này.")
    return user


def audit(db: Session, actor: User, action: str, target: str) -> None:
    db.add(AdminAudit(actor_id=actor.id, action=action, target=target))


@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    distribution = db.query(Diagnosis.prediction, func.count(Diagnosis.id)).group_by(Diagnosis.prediction).all()
    recent = db.query(Diagnosis).order_by(Diagnosis.created_at.desc()).limit(10).all()
    activities = db.query(ClientActivity.platform, func.count(ClientActivity.id)).group_by(ClientActivity.platform).all()
    return {
        "total_users": db.query(User).count(),
        "total_scans": db.query(Diagnosis).count(),
        "total_staff": db.query(User).filter(User.role.in_(["admin", "employee"])).count(),
        "disease_distribution": [{"name": name, "value": count} for name, count in distribution],
        "client_activity": [{"platform": platform, "events": count} for platform, count in activities],
        "recent_scans": [{
            "id": item.id, "user": (item.owner.full_name if item.owner else "Người dùng") if _.role == "admin" else "Ẩn danh",
            "prediction": item.prediction, "confidence": item.confidence,
            "created_at": item.created_at.isoformat(),
        } for item in recent],
    }


@router.get("/live")
def get_live_activity(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=PRESENCE_WINDOW_SECONDS)
    rows = db.query(ActiveClient.platform, func.count(ActiveClient.key)).filter(
        ActiveClient.last_seen >= cutoff
    ).group_by(ActiveClient.platform).all()
    by_platform = {platform: count for platform, count in rows}
    active_users = db.query(func.count(func.distinct(ActiveClient.user_id))).filter(
        ActiveClient.last_seen >= cutoff
    ).scalar() or 0
    return {
        "active_users": active_users,
        "active_devices": sum(by_platform.values()),
        "by_platform": by_platform,
        "presence_window_seconds": PRESENCE_WINDOW_SECONDS,
        "sampled_at": now.isoformat() + "Z",
        "diagnoses": monitor.snapshot(),
        "diagnosis_queue_limit": monitor.max_in_flight,
    }


@router.get("/content")
def list_content(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    rows = {row.slug: row for row in db.query(DiseaseContent).all()}
    result = []
    for item in load_disease_library():
        row = rows.get(item["slug"])
        draft = json.loads(row.draft_json) if row else {key: item.get(key, "") for key in EDITABLE_FIELDS}
        published = json.loads(row.published_json) if row and row.published_json else None
        result.append({
            "slug": item["slug"], "display_name_vi": item["display_name_vi"],
            "draft": draft, "published": published,
            "has_unpublished_changes": bool(row and (published is None or draft != published)),
            "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
            "published_at": row.published_at.isoformat() if row and row.published_at else None,
        })
    return result


class ContentEdit(BaseModel):
    overview: str = Field(min_length=10, max_length=2000)
    symptoms: str = Field(min_length=10, max_length=2000)
    favorable_conditions: str = Field(min_length=10, max_length=2000)
    prevention: str = Field(min_length=10, max_length=2000)
    ipm_advice: str = Field(min_length=10, max_length=2000)


@router.put("/content/{slug}")
def save_draft(slug: str, payload: ContentEdit, db: Session = Depends(get_db), actor: User = Depends(require_staff)):
    if slug not in {item["slug"] for item in load_disease_library()}:
        raise HTTPException(404, "Lớp bệnh không thuộc mô hình 7 lớp.")
    draft = {key: getattr(payload, key).strip() for key in EDITABLE_FIELDS}
    row = db.get(DiseaseContent, slug)
    if row is None:
        row = DiseaseContent(slug=slug, draft_json=json.dumps(draft, ensure_ascii=False))
        db.add(row)
    else:
        row.draft_json = json.dumps(draft, ensure_ascii=False)
    row.updated_by = actor.id
    row.updated_at = datetime.utcnow()
    audit(db, actor, "save_draft", slug)
    db.commit()
    return {"success": True}


@router.post("/content/{slug}/publish")
def publish_content(slug: str, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    row = db.get(DiseaseContent, slug)
    if row is None:
        raise HTTPException(404, "Chưa có bản nháp để xuất bản.")
    row.published_json = row.draft_json
    row.published_at = datetime.utcnow()
    audit(db, actor, "publish_content", slug)
    db.commit()
    return {"success": True}


@router.get("/mobile")
def mobile_activity(db: Session = Depends(get_db), _: User = Depends(require_staff)):
    rows = db.query(ClientActivity).order_by(ClientActivity.created_at.desc()).limit(500).all()
    by_version = {}
    for row in rows:
        key = (row.platform, row.app_version)
        by_version[key] = by_version.get(key, 0) + 1
    return {
        "versions": [{"platform": platform, "version": version, "events": count}
                     for (platform, version), count in sorted(by_version.items())],
        "recent": [{"platform": row.platform, "version": row.app_version,
                    "event": row.event, "at": row.created_at.isoformat()} for row in rows[:30]],
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).order_by(User.id.desc()).limit(200).all()
    return [{"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role} for user in users]


class StaffInvite(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    full_name: str = Field(min_length=2, max_length=80)
    role: str


@router.post("/staff")
def invite_staff(payload: StaffInvite, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Địa chỉ email không hợp lệ.")
    if payload.role not in {"admin", "employee"}:
        raise HTTPException(422, "Chỉ có thể cấp vai trò Admin hoặc Employee.")
    if not FIREBASE_ADMIN_READY:
        raise HTTPException(503, "Firebase Admin chưa được cấu hình.")
    created_firebase = False
    try:
        firebase_auth.get_user_by_email(email)
    except firebase_auth.UserNotFoundError:
        firebase_auth.create_user(email=email, display_name=payload.full_name.strip(),
                                  password=secrets.token_urlsafe(32), email_verified=False)
        created_firebase = True
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, full_name=payload.full_name.strip(),
                    hashed_password="!firebase-only-" + secrets.token_urlsafe(32), role=payload.role)
        db.add(user)
    else:
        user.full_name = payload.full_name.strip()
        user.role = payload.role
    audit(db, actor, "invite_staff", email)
    db.commit()
    return {"email": email, "role": payload.role, "created_firebase": created_firebase}


class RoleChange(BaseModel):
    role: str


@router.put("/users/{user_id}/role")
def set_user_role(user_id: int, payload: RoleChange, db: Session = Depends(get_db), actor: User = Depends(require_admin)):
    if payload.role not in {"farmer", "employee", "admin"}:
        raise HTTPException(422, "Vai trò không hợp lệ.")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Không tìm thấy tài khoản.")
    if target.id == actor.id and payload.role != "admin":
        raise HTTPException(409, "Không thể tự gỡ quyền Admin của mình.")
    if target.role == "admin" and payload.role != "admin":
        other_admins = db.query(User).filter(User.role == "admin", User.id != target.id).count()
        if other_admins == 0:
            raise HTTPException(409, "Hệ thống phải còn ít nhất một Admin.")
    target.role = payload.role
    audit(db, actor, "change_role", f"{target.email}:{payload.role}")
    db.commit()
    return {"success": True}


@router.get("/audit")
def list_audit(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    rows = db.query(AdminAudit).order_by(AdminAudit.created_at.desc()).limit(100).all()
    return [{"action": row.action, "target": row.target,
             "actor": row.actor_id, "at": row.created_at.isoformat()} for row in rows]
