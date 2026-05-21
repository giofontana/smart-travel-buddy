import json
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.graph.itinerary import parse_itinerary_json


def test_parse_itinerary_json_from_response():
    itinerary_data = {
        "destination": "Tokyo, Japan",
        "dates": {"start": "2026-07-10", "end": "2026-07-14"},
        "currency": {"from": "USD", "to": "JPY", "rate": 149.5},
        "packing": ["light rain jacket"],
        "cultural_tips": ["Bow when greeting"],
        "days": [
            {
                "date": "2026-07-10",
                "weather": {"temp_high": 31, "temp_low": 24, "condition": "Partly cloudy", "icon": "02d"},
                "activities": [{"name": "Senso-ji Temple", "time": "morning", "description": "Historic temple", "tip": "Go early"}],
            }
        ],
    }

    response_text = f"Here is your itinerary:\n```json\n{json.dumps(itinerary_data)}\n```"

    result = parse_itinerary_json(response_text)
    assert result is not None
    assert result["destination"] == "Tokyo, Japan"
    assert len(result["days"]) == 1
    assert result["days"][0]["activities"][0]["name"] == "Senso-ji Temple"


def test_parse_itinerary_json_no_json():
    result = parse_itinerary_json("Here is a plain text response with no JSON.")
    assert result is None
