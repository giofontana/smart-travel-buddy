import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from smart_travel_buddy.ws.handler import WebSocketHandler

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Smart Travel Buddy", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    handler = WebSocketHandler(websocket)
    try:
        await handler.run()
    except WebSocketDisconnect:
        await handler.cleanup()
