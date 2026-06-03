import time
import uuid
from typing import Any, Callable, Coroutine

BroadcastFn = Callable[[str, dict], Coroutine[Any, Any, None]]


class TraceEmitter:
    def __init__(self, broadcast: BroadcastFn):
        self._broadcast = broadcast
        self._request_id = str(uuid.uuid4())[:8]
        self._starts: dict[str, float] = {}

    async def start(self, source: str, target: str, label: str):
        now = time.time()
        key = f"{source}->{target}"
        self._starts[key] = now
        await self._broadcast("trace", {
            "source": source,
            "target": target,
            "status": "started",
            "label": label,
            "timestamp": now,
            "request_id": self._request_id,
        })

    async def end(self, source: str, target: str, label: str, **extra):
        now = time.time()
        key = f"{target}->{source}"
        start_time = self._starts.pop(key, now)
        duration_ms = int((now - start_time) * 1000)
        data = {
            "source": source,
            "target": target,
            "status": "completed",
            "label": label,
            "timestamp": now,
            "duration_ms": duration_ms,
            "request_id": self._request_id,
            **extra,
        }
        await self._broadcast("trace", data)
