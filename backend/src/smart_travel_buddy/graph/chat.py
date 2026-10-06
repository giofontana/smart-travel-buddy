import json

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from smart_travel_buddy import guardrails
from smart_travel_buddy.graph.itinerary import parse_itinerary_json
from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.prompts.chat import CHAT_SYSTEM_PROMPT


def _is_itinerary_reply(message: BaseMessage) -> bool:
    """The raw itinerary generation reply; the itinerary is already in the system prompt."""
    if not isinstance(message, AIMessage) or not isinstance(message.content, str):
        return False
    parsed = parse_itinerary_json(message.content)
    return isinstance(parsed, dict) and "days" in parsed


def build_chat_system_prompt(state: TravelState) -> str:
    dates = state.get("dates") or {}
    return CHAT_SYSTEM_PROMPT.format(
        destination=state.get("destination") or "unknown",
        start=dates.get("start", "unknown"),
        end=dates.get("end", "unknown"),
        budget=state.get("budget") or "mid-range",
        interests=", ".join(state.get("interests") or []) or "none",
        constraints=", ".join(state.get("constraints") or []) or "none",
        itinerary=json.dumps(state.get("itinerary") or {}, indent=2),
    )


async def chat_node(state: TravelState, config: RunnableConfig) -> TravelState:
    """General chat after the itinerary is done. Never changes the itinerary."""
    llm = config["configurable"]["llm"]
    trace = config["configurable"].get("trace")

    history = [m for m in state["messages"] if not _is_itinerary_reply(m)]
    messages = [SystemMessage(content=build_chat_system_prompt(state))] + history

    if trace:
        await trace.start("backend", "llm", "Generating chat response")

    response = await llm.ainvoke(messages)

    if trace:
        token_usage = response.response_metadata.get("token_usage", {})
        await trace.end("llm", "backend", "Chat response received", tokens=token_usage)

    if config["configurable"].get("guardrails") and await _output_blocked(response.content, trace):
        response = AIMessage(content=guardrails.CHAT_OUTPUT_REFUSAL)

    return {**state, "messages": list(state["messages"]) + [response]}


async def _output_blocked(content: str, trace) -> bool:
    if trace:
        await trace.start("backend", "guardrails", "Checking chat response")
    result = await guardrails.check([{"role": "assistant", "content": content}])
    if trace:
        await trace.end(
            "guardrails", "backend", "Chat response blocked" if result.blocked else "Chat response allowed",
            rails=result.rails,
        )
    return result.blocked
