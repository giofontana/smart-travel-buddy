from typing import Any
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

class TravelState(TypedDict):
    messages: list[BaseMessage]
    destination: str
    dates: dict | None
    interests: list[str]
    budget: str
    constraints: list[str]
    phase: str
    research_results: dict[str, Any]
    itinerary: dict | None
