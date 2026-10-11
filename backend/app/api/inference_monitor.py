"""Single-process counters for CPU inference on the laptop."""

import os
from threading import Lock

from starlette.concurrency import run_in_threadpool


class InferenceBusyError(Exception):
    """The laptop has reached its bounded inference queue."""


class InferenceMonitor:
    def __init__(self, max_in_flight: int = 20) -> None:
        self._state_lock = Lock()
        self._model_lock = Lock()
        self._in_flight = 0
        self._processing = 0
        self.max_in_flight = max(1, max_in_flight)

    async def run(self, predictor, image):
        with self._state_lock:
            if self._in_flight >= self.max_in_flight:
                raise InferenceBusyError()
            self._in_flight += 1
        try:
            return await run_in_threadpool(self._run_locked, predictor, image)
        finally:
            with self._state_lock:
                self._in_flight -= 1

    def _run_locked(self, predictor, image):
        # Grad-CAM attaches hooks to a shared model; keep one inference at a time.
        with self._model_lock:
            with self._state_lock:
                self._processing += 1
            try:
                return predictor(image)
            finally:
                with self._state_lock:
                    self._processing -= 1

    def snapshot(self) -> dict[str, int]:
        with self._state_lock:
            return {
                "processing": self._processing,
                "waiting": max(0, self._in_flight - self._processing),
            }


monitor = InferenceMonitor(max_in_flight=int(os.getenv("RICEAI_MAX_IN_FLIGHT", "20")))
