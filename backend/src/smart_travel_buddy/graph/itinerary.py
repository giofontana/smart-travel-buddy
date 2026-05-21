import json
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.prompts.itinerary import ITINERARY_SYSTEM_PROMPT


def parse_itinerary_json(text: str) -> dict | None:
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def _build_research_context(state: TravelState) -> str:
    parts = []
    results = state["research_results"]

    if "weather" in results:
        parts.append(f"## Weather Forecast\n{json.dumps(results['weather'], indent=2)}")

    if "currency" in results:
        parts.append(f"## Currency\n{json.dumps(results['currency'], indent=2)}")

    if "wikipedia" in results:
        wiki = results["wikipedia"]
        if isinstance(wiki, dict):
            parts.append(f"## Destination Info\n{wiki.get('extract', '')}")
        else:
            parts.append(f"## Destination Info\n{wiki}")

    if "rag_context" in results:
        parts.append(f"## Travel Knowledge\n{results['rag_context']}")

    return "\n\n".join(parts)


async def itinerary_node(state: TravelState, config) -> TravelState:
    llm = config["configurable"]["llm"]
    broadcast = config["configurable"]["broadcast"]

    await broadcast("progress", {"step": "itinerary", "status": "started", "label": "Generating your itinerary..."})

    research_context = _build_research_context(state)

    user_request = (
        f"Create a travel itinerary for {state['destination']} "
        f"from {state['dates']['start']} to {state['dates']['end']}.\n"
        f"Interests: {', '.join(state['interests'])}.\n"
        f"Budget: {state['budget'] or 'mid-range'}.\n"
        f"Constraints: {', '.join(state['constraints']) or 'none'}.\n\n"
        f"Research data:\n{research_context}"
    )

    messages = [
        SystemMessage(content=ITINERARY_SYSTEM_PROMPT),
        HumanMessage(content=user_request),
    ]

    response = await llm.ainvoke(messages)

    itinerary = parse_itinerary_json(response.content)

    new_messages = list(state["messages"]) + [response]
    await broadcast("progress", {"step": "itinerary", "status": "complete"})

    if itinerary:
        await broadcast("itinerary", {"data": itinerary})

    return {
        **state,
        "messages": new_messages,
        "itinerary": itinerary,
        "phase": "refinement",
    }


def build_itinerary_graph() -> StateGraph:
    graph = StateGraph(TravelState)
    graph.add_node("generate", itinerary_node)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "__end__")
    return graph
