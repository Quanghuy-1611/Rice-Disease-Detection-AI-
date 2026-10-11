"""Run with: python -m tests.test_plans (isolated in-memory database)."""

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import plans
from app.api.plans import (ActivateRequest, GrantRequest, activate_request,
                           current_period, grant_plus, plan_status,
                           refund_request, request_plus, reserve_request)
from app.database import Base
from app.models import User


def check():
    assert current_period(datetime(2026, 10, 31, 16, 59)) == "2026-10"
    assert current_period(datetime(2026, 10, 31, 17, 0)) == "2026-11"
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        farmer = User(email="farmer@test.local", full_name="Farmer", role="farmer", hashed_password="!")
        admin = User(email="admin@test.local", full_name="Admin", role="admin", hashed_password="!")
        employee = User(email="employee@test.local", full_name="Employee", role="employee", hashed_password="!")
        buyer = User(email="buyer@test.local", full_name="Buyer", role="farmer", hashed_password="!")
        db.add_all([farmer, admin, employee, buyer])
        db.commit()
        assert plan_status(db, farmer)["remaining"] == 15
        for remaining in range(14, -1, -1):
            assert reserve_request(db, farmer, "basic") is True
            assert plan_status(db, farmer)["remaining"] == remaining
        try:
            reserve_request(db, farmer, "basic")
            raise AssertionError("Basic exceeded 15 requests")
        except HTTPException as error:
            assert error.status_code == 429
        refund_request(db, farmer, "basic")
        assert plan_status(db, farmer)["remaining"] == 1
        assert reserve_request(db, admin, "plus") is False
        assert reserve_request(db, employee, "plus") is False
        assert plan_status(db, admin)["unlimited"]
        try:
            grant_plus(GrantRequest(user_id=farmer.id, days=30, reason="demo"), db, employee)
            raise AssertionError("Employee granted Plus")
        except HTTPException as error:
            assert error.status_code == 403
        grant_plus(GrantRequest(user_id=farmer.id, days=30, reason="demo"), db, admin)
        status = plan_status(db, farmer)
        assert status["plan"] == "plus" and status["remaining"] == 80
        try:
            reserve_request(db, farmer, "basic")
            raise AssertionError("Plus user used Basic bucket")
        except HTTPException as error:
            assert error.status_code == 403
        for _ in range(40):
            assert reserve_request(db, farmer, "plus")
        assert plan_status(db, farmer)["halfway_notice"]
        assert plan_status(db, farmer)["remaining"] == 40
        assert plan_status(db, farmer, datetime.utcnow() + timedelta(days=31))["plan"] == "basic"
        with patch.object(plans, "plus_model_ready", return_value=True):
            order = request_plus(db, buyer)
            assert order["price_vnd"] == 29000
            assert request_plus(db, buyer)["request_id"] == order["request_id"]
            try:
                activate_request(order["request_id"], ActivateRequest(payment_verified=False), db, admin)
                raise AssertionError("Unverified payment was activated")
            except HTTPException as error:
                assert error.status_code == 422
            try:
                activate_request(order["request_id"], ActivateRequest(payment_verified=True), db, employee)
                raise AssertionError("Employee activated a payment")
            except HTTPException as error:
                assert error.status_code == 403
            activate_request(order["request_id"], ActivateRequest(payment_verified=True), db, admin)
            assert plan_status(db, buyer)["plan"] == "plus"
            try:
                activate_request(order["request_id"], ActivateRequest(payment_verified=True), db, admin)
                raise AssertionError("Payment activated twice")
            except HTTPException as error:
                assert error.status_code == 409
    engine.dispose()

    with TemporaryDirectory() as directory:
        concurrent_engine = create_engine(f"sqlite:///{Path(directory) / 'quota.db'}",
                                          connect_args={"check_same_thread": False, "timeout": 10})
        Base.metadata.create_all(concurrent_engine)
        sessions = sessionmaker(bind=concurrent_engine)
        with sessions() as db:
            db.add(User(email="concurrent@test.local", full_name="Concurrent", role="farmer", hashed_password="!"))
            db.commit()

        def reserve_once(_):
            with sessions() as db:
                user = db.query(User).filter_by(email="concurrent@test.local").one()
                try:
                    return reserve_request(db, user, "basic")
                except HTTPException as error:
                    assert error.status_code == 429
                    return False

        with ThreadPoolExecutor(max_workers=8) as pool:
            attempts = list(pool.map(reserve_once, range(25)))
        assert sum(attempts) == 15
        concurrent_engine.dispose()


if __name__ == "__main__":
    check()
    print("Plan and quota checks passed")
