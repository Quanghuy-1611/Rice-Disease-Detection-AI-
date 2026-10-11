"""Full ASGI smoke test for quotas and refund without touching live data."""

import asyncio
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app.api import predict as predict_api
from app.api.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import User


async def check():
    with TemporaryDirectory() as directory:
        engine = create_engine(URL.create("sqlite", database=str(Path(directory) / "test.db")),
                               connect_args={"check_same_thread": False, "timeout": 10})
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine)
        with sessions() as db:
            db.add(User(email="test@riceai.local", full_name="Test", role="farmer", hashed_password="!"))
            db.commit()
        def test_db():
            with sessions() as db:
                yield db
        app.dependency_overrides[get_db] = test_db
        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="test@riceai.local", role="farmer")
        old_dir = predict_api.UPLOAD_DIR
        predict_api.UPLOAD_DIR = Path(directory) / "uploads"
        image = Image.effect_noise((224, 224), 50).convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        async def predicted(*_args):
            return "brown_spot", .99, None
        async def failed(*_args):
            raise RuntimeError("simulated inference error")
        async def send(client, data=buffer.getvalue()):
            return await client.post("/api/predict", files={"file": ("rice.jpg", data, "image/jpeg")})
        try:
            with patch.object(predict_api.model, "model", object()), patch.object(predict_api.monitor, "run", predicted):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                              base_url="http://riceai.local") as client:
                    invalid = await send(client, b"not an image")
                    assert invalid.status_code == 400
                    flat = BytesIO()
                    Image.new("RGB", (224, 224), (120, 170, 80)).save(flat, format="JPEG")
                    assert (await send(client, flat.getvalue())).status_code == 422
                    for remaining in range(14, -1, -1):
                        response = await send(client)
                        assert response.status_code == 200, response.text
                        assert response.json()["plan"]["remaining"] == remaining
                    blocked = await send(client)
                    assert blocked.status_code == 429, blocked.text
            with sessions() as db:
                from app.models import MonthlyUsage
                row = db.query(MonthlyUsage).one()
                assert row.used == 15
                row.used = 14
                db.commit()
            with patch.object(predict_api.model, "model", object()), patch.object(predict_api.monitor, "run", failed):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                              base_url="http://riceai.local") as client:
                    response = await send(client)
                    assert response.status_code == 500
            with sessions() as db:
                assert db.query(MonthlyUsage).one().used == 14
            predict_api.UPLOAD_DIR = Path(directory) / "test.db"
            with patch.object(predict_api.model, "model", object()), patch.object(predict_api.monitor, "run", predicted):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                              base_url="http://riceai.local") as client:
                    assert (await send(client)).status_code == 500
            with sessions() as db:
                assert db.query(MonthlyUsage).one().used == 14
        finally:
            predict_api.UPLOAD_DIR = old_dir
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
    print("Prediction quota API checks passed")
