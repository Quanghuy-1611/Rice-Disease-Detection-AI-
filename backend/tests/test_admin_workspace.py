"""Run with: python -m tests.test_admin_workspace (isolated SQLite)."""
from datetime import datetime, timedelta

from fastapi import HTTPException
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import ContentEdit, RoleChange, StaffInvite, get_live_activity, invite_staff, list_content, mobile_activity, publish_content, require_admin, require_staff, save_draft, set_user_role
from app.api.client import Heartbeat, heartbeat
from app.api.auth import UserLogin, login
from app.api.disease_library import get_disease_library
from app.database import Base
from app.models import ActiveClient, User


def check():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        farmer = User(email="farmer@test.local", full_name="Farmer", role="farmer", hashed_password="!")
        employee = User(email="employee@test.local", full_name="Employee", role="employee", hashed_password="!")
        admin = User(email="admin@test.local", full_name="Admin", role="admin", hashed_password="!")
        db.add_all([farmer, employee, admin])
        db.commit()
        for gate, actor, expected in [(require_staff, farmer, 403), (require_admin, employee, 403)]:
            try:
                gate(actor)
                raise AssertionError("Permission gate allowed wrong role")
            except HTTPException as error:
                assert error.status_code == expected
        assert require_staff(employee) == employee
        assert require_admin(admin) == admin
        original = get_disease_library(db)["data"][0]
        slug = original["slug"]
        draft = ContentEdit(
            overview="Nội dung thử nghiệm chưa xuất bản.",
            symptoms="Dấu hiệu thử nghiệm chi tiết.",
            favorable_conditions="Điều kiện thử nghiệm chi tiết.",
            prevention="Biện pháp phòng ngừa thử nghiệm.",
            ipm_advice="Khuyến nghị thử nghiệm có kiểm tra.",
        )
        assert save_draft(slug, draft, db, employee)["success"]
        assert list_content(db, employee)[0]["has_unpublished_changes"]
        assert get_disease_library(db)["data"][0]["overview"] == original["overview"]
        assert publish_content(slug, db, admin)["success"]
        assert get_disease_library(db)["data"][0]["overview"] == draft.overview
        assert heartbeat(Heartbeat(platform="ios", app_version="1.0.0+1"), db, employee)["success"]
        assert mobile_activity(db, employee)["versions"][0]["version"] == "1.0.0+1"
        first_id = "11111111111111111111111111111111"
        second_id = "22222222222222222222222222222222"
        for _ in range(2):
            assert heartbeat(Heartbeat(platform="ios", app_version="1.0.0+1", client_id=first_id), db, employee)["success"]
        assert heartbeat(Heartbeat(platform="web", app_version="web-1", client_id=second_id), db, admin)["success"]
        live = get_live_activity(db, employee)
        assert live["active_users"] == 2
        assert live["active_devices"] == 2
        assert live["by_platform"] == {"ios": 1, "web": 1}
        assert heartbeat(Heartbeat(platform="web", app_version="web-1", client_id="33333333333333333333333333333333"), db, employee)["success"]
        live = get_live_activity(db, employee)
        assert live["active_users"] == 2
        assert live["active_devices"] == 3
        assert db.query(ActiveClient).count() == 3
        ios_client = db.query(ActiveClient).filter_by(platform="ios").one()
        ios_client.last_seen = datetime.utcnow() - timedelta(seconds=121)
        db.commit()
        live = get_live_activity(db, admin)
        assert live["active_devices"] == 2
        assert live["active_users"] == 2
        try:
            set_user_role(admin.id, RoleChange(role="farmer"), db, admin)
            raise AssertionError("Admin self-demotion was allowed")
        except HTTPException as error:
            assert error.status_code == 409
        with patch("app.api.admin.FIREBASE_ADMIN_READY", True), patch("app.api.admin.firebase_auth.get_user_by_email"):
            result = invite_staff(StaffInvite(email="new@test.local", full_name="New Employee", role="employee"), db, admin)
            assert result["role"] == "employee"
            assert db.query(User).filter(User.email == "new@test.local").first().role == "employee"
        try:
            login(UserLogin(email="admin@test.local", password="admin123"), db)
            raise AssertionError("Legacy password login still works")
        except HTTPException as error:
            assert error.status_code == 410
    engine.dispose()


if __name__ == "__main__":
    check()
    print("Admin workspace checks passed")
