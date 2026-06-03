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


@pytest.mark.asyncio
async def test_interview_node_emits_llm_traces():
    from langchain_core.messages import HumanMessage, AIMessage
    from unittest.mock import AsyncMock

    trace_events = []
    async def capture_broadcast(event_type, data):
        if event_type == "trace":
            trace_events.append(data)

    trace = TraceEmitter(capture_broadcast)

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content="Where do you want to go?")

    state = {
        "messages": [HumanMessage(content="Hi")],
        "destination": "", "dates": None, "interests": [],
        "budget": "", "constraints": [], "phase": "interview",
        "research_results": {}, "itinerary": None,
    }

    config = {"configurable": {"llm": mock_llm, "trace": trace}}

    from smart_travel_buddy.graph.interview import interview_node
    await interview_node(state, config)

    sources_targets = [(e["source"], e["target"]) for e in trace_events]
    assert ("backend", "llm") in sources_targets
    assert ("llm", "backend") in sources_targets


@pytest.mark.asyncio
async def test_call_weather_emits_mcp_traces():
    import json
    from unittest.mock import AsyncMock

    trace_events = []
    async def capture_broadcast(event_type_or_dict, data=None):
        if isinstance(event_type_or_dict, str) and event_type_or_dict == "trace":
            trace_events.append(data)

    trace = TraceEmitter(capture_broadcast)

    mock_tool = AsyncMock()
    mock_tool.name = "get_forecast"
    mock_tool.ainvoke.return_value = json.dumps({"city": "Tokyo", "forecast": []})

    state = {
        "messages": [], "destination": "Tokyo, Japan",
        "dates": {"start": "2026-07-10", "end": "2026-07-14"},
        "interests": ["food"], "budget": "mid-range", "constraints": [],
        "phase": "research", "research_results": {}, "itinerary": None,
    }

    config = {"configurable": {
        "mcp_tools": {"weather": [mock_tool]},
        "broadcast": capture_broadcast,
        "trace": trace,
    }}

    from smart_travel_buddy.graph.research import call_weather
    await call_weather(state, config)

    sources_targets = [(e["source"], e["target"]) for e in trace_events]
    assert ("backend", "mcp-weather") in sources_targets
    assert ("mcp-weather", "backend") in sources_targets


@pytest.mark.asyncio
async def test_itinerary_node_emits_llm_traces():
    from langchain_core.messages import AIMessage
    from unittest.mock import AsyncMock

    trace_events = []
    async def capture_broadcast(event_type, data=None):
        if event_type == "trace":
            trace_events.append(data)

    trace = TraceEmitter(capture_broadcast)

    mock_llm = AsyncMock()
    mock_llm.ainvoke.return_value = AIMessage(content='```json\n{"title":"Tokyo Trip","days":[]}\n```')

    state = {
        "messages": [], "destination": "Tokyo, Japan",
        "dates": {"start": "2026-07-10", "end": "2026-07-14"},
        "interests": ["food"], "budget": "mid-range", "constraints": [],
        "phase": "research", "research_results": {
            "weather": "{}", "currency": "{}", "wikipedia": "Tokyo info", "rag_context": "",
        }, "itinerary": None,
    }

    config = {"configurable": {"llm": mock_llm, "broadcast": capture_broadcast, "trace": trace}}

    from smart_travel_buddy.graph.itinerary import itinerary_node
    await itinerary_node(state, config)

    sources_targets = [(e["source"], e["target"]) for e in trace_events]
    assert ("backend", "llm") in sources_targets
    assert ("llm", "backend") in sources_targets
