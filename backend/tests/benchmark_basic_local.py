"""Measure a small burst through the full Basic ASGI route without touching live data.

Run from backend: python -m tests.benchmark_basic_local
This is a laptop smoke benchmark, not a production capacity rating.
"""

import asyncio
from collections import Counter
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

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


async def measure(client: httpx.AsyncClient, image_bytes: bytes, count: int) -> None:
    async def request() -> int:
        response = await client.post(
            "/api/predict",
            files={"file": ("sample.jpg", image_bytes, "image/jpeg")},
            data={"analysis_mode": "basic"},
            headers={"X-RiceAI-Client": "web", "X-RiceAI-Version": "benchmark"},
        )
        return response.status_code

    started = perf_counter()
    statuses = await asyncio.gather(*(request() for _ in range(count)))
    print(f"{count} concurrent requests: {perf_counter() - started:.2f}s; HTTP {dict(Counter(statuses))}")


async def run() -> None:
    with TemporaryDirectory() as directory:
        engine = create_engine(
            URL.create("sqlite", database=str(Path(directory) / "benchmark.db")),
            connect_args={"check_same_thread": False, "timeout": 10},
        )
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine)
        with sessions() as db:
            db.add(User(email="benchmark@local.test", full_name="Benchmark", role="admin"))
            db.commit()

        def test_db():
            with sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="benchmark@local.test", role="admin")
        original_upload_dir = predict_api.UPLOAD_DIR
        predict_api.UPLOAD_DIR = Path(directory) / "uploads"
        image = Image.new("RGB", (224, 224), (110, 155, 90))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://riceai-test.local",
                timeout=30,
            ) as client:
                for count in (1, 5, 10, 20, 25):
                    await measure(client, buffer.getvalue(), count)
        finally:
            app.dependency_overrides.clear()
            predict_api.UPLOAD_DIR = original_upload_dir
            engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
