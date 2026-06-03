import time
from unittest.mock import AsyncMock

import pytest

from smart_travel_buddy.trace import TraceEmitter


@pytest.mark.asyncio
async def test_start_emits_trace_event():
    broadcast = AsyncMock()
    emitter = TraceEmitter(broadcast)

    await emitter.start("backend", "llm", "Calling LLM")

    broadcast.assert_called_once()
    call_args = broadcast.call_args
    assert call_args[0][0] == "trace"
    data = call_args[0][1]
    assert data["source"] == "backend"
    assert data["target"] == "llm"
    assert data["status"] == "started"
    assert data["label"] == "Calling LLM"
    assert "timestamp" in data
    assert "request_id" in data


@pytest.mark.asyncio
async def test_end_emits_trace_with_duration():
    broadcast = AsyncMock()
    emitter = TraceEmitter(broadcast)

    await emitter.start("backend", "llm", "Calling LLM")
    await emitter.end("llm", "backend", "LLM responded")

    assert broadcast.call_count == 2
    end_data = broadcast.call_args_list[1][0][1]
    assert end_data["source"] == "llm"
    assert end_data["target"] == "backend"
    assert end_data["status"] == "completed"
    assert end_data["label"] == "LLM responded"
    assert "duration_ms" in end_data
    assert isinstance(end_data["duration_ms"], int)


@pytest.mark.asyncio
async def test_request_id_consistent_within_emitter():
    broadcast = AsyncMock()
    emitter = TraceEmitter(broadcast)

    await emitter.start("backend", "llm", "Call 1")
    await emitter.start("backend", "rag", "Call 2")

    id1 = broadcast.call_args_list[0][0][1]["request_id"]
    id2 = broadcast.call_args_list[1][0][1]["request_id"]
    assert id1 == id2


@pytest.mark.asyncio
async def test_new_request_generates_new_id():
    broadcast = AsyncMock()
    emitter1 = TraceEmitter(broadcast)
    emitter2 = TraceEmitter(broadcast)

    await emitter1.start("backend", "llm", "Req 1")
    await emitter2.start("backend", "llm", "Req 2")

    id1 = broadcast.call_args_list[0][0][1]["request_id"]
    id2 = broadcast.call_args_list[1][0][1]["request_id"]
    assert id1 != id2


@pytest.mark.asyncio
async def test_duration_tracks_correct_pair():
    broadcast = AsyncMock()
    emitter = TraceEmitter(broadcast)

    await emitter.start("backend", "mcp-weather", "Weather")
    await emitter.start("backend", "mcp-currency", "Currency")
    await emitter.end("mcp-weather", "backend", "Weather done")

    end_data = broadcast.call_args_list[2][0][1]
    assert end_data["source"] == "mcp-weather"
    assert end_data["target"] == "backend"
    assert end_data["duration_ms"] >= 0
