"""Server-side plan and monthly diagnosis limits shared by web and mobile."""

from datetime import datetime, timedelta, timezone
from calendar import monthrange
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models import (AdminAudit, MonthlyUsage, PlanGrant, PlusPaymentVerification,
                        PlusRequest, PlusTrial, User)

router = APIRouter()
LIMITS = {"basic": 15, "plus": 80}
STAFF = {"admin", "employee"}
MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
RELEASE_WEIGHTS = (
    "mobilenetv3large_7class_seed42.pt",
    "swin_tiny_plus_7class.pt",
    "deeplabv3plus_plus_lesion.pt",
)
VIETNAM_TIME = timezone(timedelta(hours=7))
_approved_runtime_fingerprints: tuple | None = None
PAYMENT_BANK_ID = os.getenv("RICEAI_PAYMENT_BANK_ID", "970407")
PAYMENT_ACCOUNT = os.getenv("RICEAI_PAYMENT_ACCOUNT", "19072045330011")
PAYMENT_NAME = os.getenv("RICEAI_PAYMENT_NAME", "DAO VIET QUANG HUY")


def one_month_after(start: datetime) -> datetime:
    year = start.year + (start.month == 12)
    month = start.month % 12 + 1
    return start.replace(year=year, month=month,
                         day=min(start.day, monthrange(year, month)[1]))


def payment_code(request_id: int) -> str:
    return f"RICEAI{request_id}"


def _eligible_account(user: User) -> bool:
    return user.role not in STAFF and not (
        user.email.startswith("guest_") and user.email.endswith("@anonymous.riceai")
    )


def current_period(now: datetime | None = None) -> str:
    """Reset monthly usage at midnight in Vietnam, independent of server timezone."""
    instant = now.replace(tzinfo=timezone.utc) if now and now.tzinfo is None else now
    return (instant or datetime.now(timezone.utc)).astimezone(VIETNAM_TIME).strftime("%Y-%m")


@lru_cache(maxsize=8)
def _release_weights_match(fingerprints: tuple, expected: tuple) -> bool:
    for (path, _size, _mtime), digest in zip(fingerprints, expected):
        hasher = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        if hasher.hexdigest() != digest:
            return False
    return True


def plus_model_ready() -> bool:
    global _approved_runtime_fingerprints
    release_path = MODEL_DIR / "plus_release.json"
    if not release_path.is_file():
        return False
    try:
        release = json.loads(release_path.read_text(encoding="utf-8"))
        if release.get("validated") is not True:
            return False
        expected = tuple(release.get("weights_sha256", {}).get(name) for name in RELEASE_WEIGHTS)
        if any(not isinstance(digest, str) or len(digest) != 64 for digest in expected):
            return False
        files = tuple(MODEL_DIR / name for name in RELEASE_WEIGHTS)
        fingerprints = tuple((str(path), path.stat().st_size, path.stat().st_mtime_ns)
                             for path in files)
        if _approved_runtime_fingerprints is not None and fingerprints != _approved_runtime_fingerprints:
            # Model objects stay in memory; a new approved model needs a server restart.
            return False
        if not _release_weights_match(fingerprints, expected):
            return False
        if _approved_runtime_fingerprints is None:
            _approved_runtime_fingerprints = fingerprints
        return True
    except (ValueError, OSError):
        return False


def active_plan(db: Session, user: User, now: datetime | None = None) -> str:
    if user.role in STAFF:
        return "plus"
    now = now or datetime.utcnow()
    grant = db.get(PlanGrant, user.id)
    trial = db.get(PlusTrial, user.id)
    return "plus" if ((grant and grant.valid_until > now) or
                      (trial and trial.valid_until > now)) else "basic"


def plan_status(db: Session, user: User, now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    plan = active_plan(db, user, now)
    period = current_period(now)
    rows = db.query(MonthlyUsage).filter(
        MonthlyUsage.user_id == user.id, MonthlyUsage.period == period
    ).all()
    usage = {row.plan: row.used for row in rows}
    unlimited = user.role in STAFF
    grant = db.get(PlanGrant, user.id) if not unlimited else None
    trial = db.get(PlusTrial, user.id) if not unlimited else None
    pending = db.query(PlusRequest).filter_by(user_id=user.id, status="pending").first() if not unlimited else None
    active_expiries = [item.valid_until for item in (grant, trial)
                       if item and item.valid_until > now]
    return {
        "plan": plan,
        "unlimited": unlimited,
        "period": period,
        "limits": LIMITS,
        "used": {name: usage.get(name, 0) for name in LIMITS},
        "remaining": None if unlimited else max(0, LIMITS[plan] - usage.get(plan, 0)),
        "halfway_notice": plan == "plus" and not unlimited and usage.get("plus", 0) >= 40,
        "valid_until": max(active_expiries).isoformat() + "Z" if active_expiries else None,
        "trial_available": _eligible_account(user) and trial is None and grant is None and plan == "basic",
        "trial_active": bool(trial and trial.valid_until > now and
                             not (grant and grant.valid_until > now)),
        "trial_valid_until": trial.valid_until.isoformat() + "Z" if trial and trial.valid_until > now else None,
        "pending_request": {"id": pending.id, "price_vnd": pending.price_vnd,
                            "payment_code": payment_code(pending.id)} if pending else None,
    }


def reserve_request(db: Session, user: User, plan: str) -> bool:
    """Atomically reserve one successful inference slot; caller refunds on failure."""
    if user.role in STAFF:
        return False
    if plan not in LIMITS or plan != active_plan(db, user):
        raise HTTPException(403, "Gói hiện tại không cho phép chức năng này.")
    period = current_period()
    db.execute(insert(MonthlyUsage).values(
        user_id=user.id, period=period, plan=plan, used=0
    ).on_conflict_do_nothing(index_elements=["user_id", "period", "plan"]))
    result = db.execute(update(MonthlyUsage).where(
        MonthlyUsage.user_id == user.id,
        MonthlyUsage.period == period,
        MonthlyUsage.plan == plan,
        MonthlyUsage.used < LIMITS[plan],
    ).values(used=MonthlyUsage.used + 1))
    db.commit()
    if result.rowcount != 1:
        raise HTTPException(429, f"Bạn đã dùng hết {LIMITS[plan]} lượt {plan.title()} trong tháng này.")
    return True


def refund_request(db: Session, user: User, plan: str) -> None:
    period = current_period()
    db.execute(update(MonthlyUsage).where(
        MonthlyUsage.user_id == user.id,
        MonthlyUsage.period == period,
        MonthlyUsage.plan == plan,
        MonthlyUsage.used > 0,
    ).values(used=MonthlyUsage.used - 1))
    db.commit()


@router.get("/me")
def my_plan(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return plan_status(db, user)


@router.get("/catalog")
def catalog():
    return {
        "basic": {"images_per_request": 1, "requests_per_month": 15},
        "plus": {"images_per_request": 5, "requests_per_month": 80,
                 "intro_price_vnd": 29000, "monthly_price_vnd": 49000,
                 "trial_months": 1},
        "payment_status": "manual_bank_transfer",
        "payment_bank": {"bank_id": PAYMENT_BANK_ID,
                         "account_number": PAYMENT_ACCOUNT,
                         "account_name": PAYMENT_NAME},
        "plus_ready": plus_model_ready(),
    }


@router.post("/start-trial")
def start_trial(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not plus_model_ready():
        raise HTTPException(503, "Plus chưa sẵn sàng để dùng thử.")
    if not _eligible_account(user):
        raise HTTPException(403, "Hãy đăng nhập bằng email đã xác minh để dùng thử Plus.")
    if active_plan(db, user) == "plus":
        raise HTTPException(409, "Tài khoản đang dùng Plus.")
    if db.get(PlusTrial, user.id) or db.get(PlanGrant, user.id):
        raise HTTPException(409, "Tài khoản không còn lượt dùng thử Plus.")
    now = datetime.utcnow()
    db.add(PlusTrial(user_id=user.id, started_at=now,
                     valid_until=one_month_after(now)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Tài khoản đã sử dụng một lần dùng thử Plus.")
    return plan_status(db, user)


@router.post("/request-plus")
def request_plus(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not plus_model_ready():
        raise HTTPException(503, "Plus chưa hoàn tất kiểm định mô hình nên chưa nhận yêu cầu thanh toán.")
    if not _eligible_account(user):
        raise HTTPException(403, "Hãy đăng nhập bằng email đã xác minh để dùng Plus.")
    grant = db.get(PlanGrant, user.id)
    if grant and grant.valid_until > datetime.utcnow():
        raise HTTPException(409, "Tài khoản đã có quyền sử dụng Plus.")
    pending = db.query(PlusRequest).filter_by(user_id=user.id, status="pending").first()
    if pending:
        return {"request_id": pending.id, "status": "pending",
                "price_vnd": pending.price_vnd, "payment_code": payment_code(pending.id)}
    earlier = db.query(PlusRequest).filter_by(user_id=user.id, status="activated").first()
    price = 49000 if earlier else 29000
    order = PlusRequest(user_id=user.id, status="pending", price_vnd=price)
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"request_id": order.id, "status": "pending", "price_vnd": price,
            "payment_code": payment_code(order.id)}


@router.get("/requests")
def list_requests(db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    if actor.role != "admin":
        raise HTTPException(403, "Chỉ Admin được xem yêu cầu Plus.")
    requests = db.query(PlusRequest).order_by(PlusRequest.created_at.desc()).limit(200).all()
    return [{"id": row.id, "email": db.get(User, row.user_id).email,
             "user_id": row.user_id, "status": row.status, "price_vnd": row.price_vnd,
             "payment_code": payment_code(row.id),
             "created_at": row.created_at.isoformat()} for row in requests]


class ActivateRequest(BaseModel):
    payment_verified: bool
    bank_reference: str = Field(min_length=3, max_length=100)
    amount_vnd: int = Field(gt=0)


@router.post("/requests/{request_id}/activate")
def activate_request(request_id: int, payload: ActivateRequest, db: Session = Depends(get_db),
                     actor: User = Depends(get_current_user)):
    if actor.role != "admin":
        raise HTTPException(403, "Chỉ Admin được kích hoạt Plus.")
    if not payload.payment_verified:
        raise HTTPException(422, "Cần xác nhận đã kiểm tra thanh toán ở bên ngoài RiceAI.")
    order = db.get(PlusRequest, request_id)
    if order is None:
        raise HTTPException(404, "Không tìm thấy yêu cầu Plus.")
    if order.status != "pending":
        raise HTTPException(409, "Yêu cầu này đã được xử lý.")
    if payload.amount_vnd != order.price_vnd:
        raise HTTPException(422, "Số tiền thực nhận không khớp yêu cầu thanh toán.")
    reference = payload.bank_reference.strip().upper()
    if len(reference) < 3:
        raise HTTPException(422, "Cần mã tham chiếu từ giao dịch ngân hàng.")
    now = datetime.utcnow()
    grant = db.get(PlanGrant, order.user_id)
    trial = db.get(PlusTrial, order.user_id)
    start = max([now] + [item.valid_until for item in (grant, trial) if item])
    valid_until = one_month_after(start)
    if grant is None:
        db.add(PlanGrant(user_id=order.user_id, valid_until=valid_until, granted_by=actor.id,
                         reason=f"manual_payment_request_{order.id}"))
    else:
        grant.valid_until = valid_until
        grant.granted_by = actor.id
        grant.reason = f"manual_payment_request_{order.id}"
    order.status = "activated"
    order.reviewed_at = now
    order.reviewed_by = actor.id
    db.add(PlusPaymentVerification(request_id=order.id, bank_reference=reference,
                                   amount_vnd=payload.amount_vnd, verified_by=actor.id))
    db.add(AdminAudit(actor_id=actor.id, action="activate_plus_request", target=str(order.id)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Mã giao dịch ngân hàng đã được dùng cho yêu cầu khác.")
    return {"user_id": order.user_id, "valid_until": valid_until.isoformat() + "Z"}


class GrantRequest(BaseModel):
    user_id: int = Field(gt=0)
    days: int = Field(default=30, ge=1, le=366)
    reason: str = Field(min_length=3, max_length=200)


@router.post("/admin/grant")
def grant_plus(payload: GrantRequest, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    if actor.role != "admin":
        raise HTTPException(403, "Chỉ Admin được cấp Plus.")
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(404, "Không tìm thấy tài khoản.")
    now = datetime.utcnow()
    grant = db.get(PlanGrant, user.id)
    valid_until = max(now, grant.valid_until) + timedelta(days=payload.days) if grant else now + timedelta(days=payload.days)
    if grant is None:
        grant = PlanGrant(user_id=user.id, valid_until=valid_until,
                          granted_by=actor.id, reason=payload.reason.strip())
        db.add(grant)
    else:
        grant.valid_until = valid_until
        grant.granted_by = actor.id
        grant.reason = payload.reason.strip()
    db.add(AdminAudit(actor_id=actor.id, action="grant_plus", target=str(user.id)))
    db.commit()
    return {"user_id": user.id, "valid_until": valid_until.isoformat() + "Z"}
