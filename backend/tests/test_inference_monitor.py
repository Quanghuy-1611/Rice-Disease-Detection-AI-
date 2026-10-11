"""Smoke-check the asynchronous boundary around the shared Grad-CAM model."""

import asyncio
from threading import Event
from time import perf_counter

from PIL import Image

from app.api.inference_monitor import InferenceBusyError, InferenceMonitor, monitor
from app.api.seven_class_model import model


async def check() -> None:
    assert await monitor.run(lambda value: value + 1, 1) == 2
    assert monitor.snapshot() == {"processing": 0, "waiting": 0}

    limited = InferenceMonitor(max_in_flight=1)
    started_event = Event()
    release_event = Event()

    def hold(_):
        started_event.set()
        release_event.wait(timeout=3)

    first = asyncio.create_task(limited.run(hold, None))
    assert await asyncio.to_thread(started_event.wait, 2)
    try:
        await limited.run(lambda _: None, None)
        raise AssertionError("Full queue admitted another prediction")
    except InferenceBusyError:
        pass
    finally:
        release_event.set()
        await first
    assert limited.snapshot() == {"processing": 0, "waiting": 0}

    image = Image.new("RGB", (224, 224), (110, 155, 90))
    started = perf_counter()
    results = await asyncio.gather(*(monitor.run(model.predict, image) for _ in range(10)))
    for label, confidence, _ in results:
        assert label in {"bacterial_leaf_blight", "brown_spot", "golden_apple_snail", "leaf_roller", "normal", "tungro", "weeds"}
        assert 0 <= confidence <= 1
    assert monitor.snapshot() == {"processing": 0, "waiting": 0}
    print(f"Ten model predictions completed in {perf_counter() - started:.3f}s")


if __name__ == "__main__":
    asyncio.run(check())
