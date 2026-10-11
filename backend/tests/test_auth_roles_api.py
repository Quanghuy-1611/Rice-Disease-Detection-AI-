"""Firebase email verification and server-side staff gates on an isolated ASGI app."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app.api import auth
from app.database import Base, get_db
from app.main import app
from app.models import User


async def check():
    with TemporaryDirectory() as directory:
        engine = create_engine(
            URL.create("sqlite", database=str(Path(directory) / "auth.db")),
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine)

        def test_db():
            with sessions() as db:
                yield db

        def verify(token, **_kwargs):
            if token == "unverified":
                return {"uid": "unverified-user", "email": "person@example.test",
                        "email_verified": False, "firebase": {"sign_in_provider": "password"}}
            if token == "verified":
                return {"uid": "verified-user", "email": "PERSON@example.test",
                        "email_verified": True, "role": "admin",
                        "firebase": {"sign_in_provider": "password"}}
            if token == "anonymous":
                return {"uid": "guest-1", "firebase": {"sign_in_provider": "anonymous"}}
            raise ValueError("invalid token")

        app.dependency_overrides[get_db] = test_db
        try:
            with patch.object(auth, "FIREBASE_ADMIN_READY", True), \
                    patch.object(auth.firebase_auth, "verify_id_token", side_effect=verify):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                              base_url="http://riceai.test") as client:
                    response = await client.post("/api/auth/firebase/exchange",
                                                 json={"id_token": "unverified"})
                    assert response.status_code == 403, response.text
                    response = await client.post("/api/auth/firebase/exchange",
                                                 json={"id_token": "verified"})
                    assert response.status_code == 200, response.text
                    payload = response.json()
                    assert payload["role"] == "farmer"  # Never trust a token's role claim.
                    headers = {"Authorization": f"Bearer {payload['access_token']}"}
                    assert (await client.get("/api/admin/stats", headers=headers)).status_code == 403
                    assert (await client.get("/api/plans/requests", headers=headers)).status_code == 403
                    assert (await client.get("/api/auth/me", headers=headers)).json()["role"] == "farmer"

                    with sessions() as db:
                        user = db.query(User).filter_by(email="person@example.test").one()
                        user.role = "employee"
                        db.commit()
                    assert (await client.get("/api/admin/stats", headers=headers)).status_code == 200
                    assert (await client.get("/api/plans/requests", headers=headers)).status_code == 403

                    guest = await client.post("/api/auth/firebase/exchange",
                                              json={"id_token": "anonymous"})
                    assert guest.status_code == 200, guest.text
                    guest_headers = {"Authorization": f"Bearer {guest.json()['access_token']}"}
                    prediction = await client.post("/api/predict", headers=guest_headers,
                                                   files={"file": ("test.jpg", b"invalid", "image/jpeg")})
                    assert prediction.status_code == 403, prediction.text
                    assert (await client.post("/api/auth/login",
                                              json={"email": "person@example.test", "password": "old"})).status_code == 410
                    assert (await client.post("/api/auth/register",
                                              json={"email": "person@example.test", "password": "old",
                                                    "full_name": "Test"})).status_code == 410
                    assert (await client.post("/api/auth/firebase/exchange",
                                              json={"id_token": "bad"})).status_code == 401
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
    print("Verified email and role API checks passed")
