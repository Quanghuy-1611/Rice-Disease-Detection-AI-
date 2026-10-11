"""Exercise Plus batches and quota on an isolated ASGI app and SQLite database."""

import asyncio
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app.api import plus_predict as api
from app.api.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import MonthlyUsage, PlanGrant, User


async def check():
    assert api.summarize_batch([{"prediction": "brown_spot"},
                                {"prediction": "brown_spot"},
                                {"prediction": None}])[0] == "brown_spot"
    assert api.summarize_batch([{"prediction": "brown_spot"},
                                {"prediction": "tungro"},
                                {"prediction": None}])[0] is None
    assert api.summarize_batch([{"prediction": None} for _ in range(5)])[0] is None
    assert api.summarize_batch([{"prediction": "brown_spot"},
                                {"prediction": "brown_spot"},
                                {"prediction": None},
                                {"prediction": None},
                                {"prediction": None}])[0] is None
    with TemporaryDirectory() as directory:
        engine = create_engine(URL.create("sqlite", database=str(Path(directory) / "test.db")),
                               connect_args={"check_same_thread": False, "timeout": 10})
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine)
        with sessions() as db:
            db.add(User(email="plus@riceai.local", full_name="Plus", role="farmer", hashed_password="!"))
            db.commit()
            db.add(PlanGrant(user_id=1, valid_until=datetime.utcnow() + timedelta(days=30),
                             granted_by=1, reason="test"))
            db.commit()

        def test_db():
            with sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        app.dependency_overrides[get_current_user] = lambda: User(
            id=1, email="plus@riceai.local", role="farmer")
        old_dir = api.UPLOAD_DIR
        api.UPLOAD_DIR = Path(directory) / "uploads"
        buffer = BytesIO()
        Image.effect_noise((224, 224), 50).convert("RGB").save(buffer, format="JPEG")
        image = buffer.getvalue()

        async def predicted(*_args):
            return {"prediction": "brown_spot", "confidence": .97,
                    "uncertain": False, "disagreement": False,
                    "mask_applied": True, "heatmap": None}

        async def failed(*_args):
            raise RuntimeError("simulated Plus failure")

        async def send(client, count, data=image):
            return await client.post("/api/predict/plus", files=[
                ("files", (f"rice-{i}.jpg", data, "image/jpeg")) for i in range(count)])

        try:
            with patch.object(api, "plus_model_ready", return_value=True), \
                    patch.object(api.monitor, "run", predicted):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                              base_url="http://riceai.local") as client:
                    assert (await send(client, 6)).status_code == 422
                    assert (await send(client, 2, b"invalid image")).status_code == 400
                    result = await send(client, 5)
                    assert result.status_code == 200, result.text
                    payload = result.json()
                    assert len(payload["images"]) == 5
                    assert payload["prediction"] == "brown_spot"
                    assert payload["plan"]["remaining"] == 79
            with sessions() as db:
                assert db.query(MonthlyUsage).one().used == 1
            api.UPLOAD_DIR = Path(directory) / "test.db"
            with patch.object(api, "plus_model_ready", return_value=True), \
                    patch.object(api.monitor, "run", predicted):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                              base_url="http://riceai.local") as client:
                    assert (await send(client, 1)).status_code == 500
            with sessions() as db:
                assert db.query(MonthlyUsage).one().used == 1
            with patch.object(api, "plus_model_ready", return_value=True), \
                    patch.object(api.monitor, "run", failed):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                              base_url="http://riceai.local") as client:
                    assert (await send(client, 1)).status_code == 500
            with sessions() as db:
                assert db.query(MonthlyUsage).one().used == 1
        finally:
            api.UPLOAD_DIR = old_dir
            app.dependency_overrides.clear()
            engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
    print("Plus batch API checks passed")
