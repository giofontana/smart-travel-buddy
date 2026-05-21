import json
from unittest.mock import AsyncMock
import pytest
from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.graph.research import call_weather, call_currency, call_wikipedia


@pytest.mark.asyncio
async def test_call_weather():
    mock_tool = AsyncMock()
    mock_tool.name = "get_forecast"
    mock_tool.ainvoke.return_value = json.dumps({
        "city": "Tokyo", "country": "JP",
        "forecast": [{"date": "2026-07-10", "temp_min": 24, "temp_max": 31, "condition": "partly cloudy", "icon": "02d"}],
    })
    state = TravelState(
        messages=[],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["food"],
        budget="mid-range",
        constraints=[],
        phase="research",
        research_results={},
        itinerary=None
    )
    result = await call_weather(state, {"configurable": {"mcp_tools": {"weather": [mock_tool]}, "broadcast": AsyncMock()}})
    assert "weather" in result["research_results"]


@pytest.mark.asyncio
async def test_call_currency():
    mock_tool = AsyncMock()
    mock_tool.name = "get_exchange_rate"
    mock_tool.ainvoke.return_value = json.dumps({"from": "USD", "to": "JPY", "rate": 149.5, "date": "2026-05-21"})
    state = TravelState(
        messages=[],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["food"],
        budget="mid-range",
        constraints=[],
        phase="research",
        research_results={},
        itinerary=None
    )
    result = await call_currency(state, {"configurable": {"mcp_tools": {"currency": [mock_tool]}, "broadcast": AsyncMock()}})
    assert "currency" in result["research_results"]


@pytest.mark.asyncio
async def test_call_wikipedia():
    mock_tool = AsyncMock()
    mock_tool.name = "get_summary"
    mock_tool.ainvoke.return_value = json.dumps({"title": "Tokyo", "extract": "Tokyo is the capital of Japan.", "description": "Capital city", "thumbnail": ""})
    state = TravelState(
        messages=[],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["culture"],
        budget="mid-range",
        constraints=[],
        phase="research",
        research_results={},
        itinerary=None
    )
    result = await call_wikipedia(state, {"configurable": {"mcp_tools": {"wikipedia": [mock_tool]}, "broadcast": AsyncMock()}})
    assert "wikipedia" in result["research_results"]
