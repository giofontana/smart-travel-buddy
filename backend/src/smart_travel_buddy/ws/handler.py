import asyncio
import json
import traceback
from fastapi import WebSocket

class WebSocketHandler:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.orchestrator = None
        self._task: asyncio.Task | None = None

    async def broadcast(self, event_type: str, data: dict):
        await self.ws.send_json({"type": event_type, **data})

    async def run(self):
        while True:
            raw = await self.ws.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await self.broadcast("error", {"message": "Invalid JSON"})
                continue
            action = message.get("action")
            if action == "start":
                await self._handle_start(message)
            elif action == "message":
                await self._handle_message(message)
            elif action == "cancel":
                await self._handle_cancel()
            else:
                await self.broadcast("error", {"message": f"Unknown action: {action}"})

    async def _handle_start(self, message: dict):
        from smart_travel_buddy.graph.orchestrator import create_orchestrator
        self.orchestrator = await create_orchestrator(self.broadcast)
        await self.broadcast("session_started", {"session_id": self.orchestrator.session_id})

    async def _handle_message(self, message: dict):
        if not self.orchestrator:
            await self.broadcast("error", {"message": "No active session. Send 'start' first."})
            return
        content = message.get("content", "")
        if self._task and not self._task.done():
            await self.broadcast("error", {"message": "Agent is busy processing. Please wait."})
            return
        self._task = asyncio.create_task(self._run_agent(content))

    async def _run_agent(self, user_message: str):
        try:
            await self.orchestrator.process_message(user_message)
        except Exception as e:
            traceback.print_exc()
            await self.broadcast("error", {"message": str(e)})

    async def _handle_cancel(self):
        if self._task and not self._task.done():
            self._task.cancel()
            await self.broadcast("cancelled", {})

    async def cleanup(self):
        if self._task and not self._task.done():
            self._task.cancel()
        if self.orchestrator:
            await self.orchestrator.close()
