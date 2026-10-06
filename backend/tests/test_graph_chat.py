import json
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from smart_travel_buddy import guardrails
from smart_travel_buddy.graph import orchestrator as orchestrator_module
from smart_travel_buddy.graph.chat import chat_node
from smart_travel_buddy.graph.orchestrator import Orchestrator

ITINERARY = {
    "destination": "Barcelona, Spain",
    "days": [{"date": "2026-11-01", "activities": [{"name": "Picasso Museum", "time": "afternoon"}]}],
}


def _chat_state():
    return {
        "messages": [
            HumanMessage(content="I want to go to Barcelona"),
            AIMessage(content="Great choice! When are you traveling?"),
            AIMessage(content=f"```json\n{json.dumps(ITINERARY)}\n```"),
            HumanMessage(content="What should I wear on day 1?"),
        ],
        "destination": "Barcelona, Spain",
        "dates": {"start": "2026-11-01", "end": "2026-11-05"},
        "interests": ["art", "food"],
        "budget": "mid-range",
        "constraints": [],
        "phase": "chat",
        "research_results": {},
        "itinerary": ITINERARY,
    }


def _chat_config(guardrails_enabled=False, reply="Comfortable shoes and a light jacket."):
    llm = AsyncMock()
    llm.ainvoke.return_value = AIMessage(content=reply)
    return {"configurable": {"llm": llm, "broadcast": AsyncMock(), "guardrails": guardrails_enabled}}


async def test_chat_uses_trip_context_and_skips_raw_itinerary_reply():
    config = _chat_config()

    await chat_node(_chat_state(), config)

    sent = config["configurable"]["llm"].ainvoke.await_args.args[0]
    assert isinstance(sent[0], SystemMessage)
    assert "Barcelona, Spain" in sent[0].content
    assert "Picasso Museum" in sent[0].content
    assert [m.content for m in sent[1:]] == [
        "I want to go to Barcelona",
        "Great choice! When are you traveling?",
        "What should I wear on day 1?",
    ]


async def test_chat_appends_reply_and_keeps_itinerary():
    result = await chat_node(_chat_state(), _chat_config())

    assert result["messages"][-1].content == "Comfortable shoes and a light jacket."
    assert result["itinerary"] == ITINERARY
    assert result["phase"] == "chat"


async def test_chat_without_guardrails_skips_check(monkeypatch):
    check = AsyncMock()
    monkeypatch.setattr(guardrails, "check", check)

    await chat_node(_chat_state(), _chat_config(guardrails_enabled=False))

    check.assert_not_awaited()


async def test_chat_blocked_reply_is_replaced(monkeypatch):
    check = AsyncMock(return_value=guardrails.GuardrailResult(blocked=True, rails=["self check output"]))
    monkeypatch.setattr(guardrails, "check", check)

    result = await chat_node(_chat_state(), _chat_config(guardrails_enabled=True, reply="something harmful"))

    check.assert_awaited_once_with([{"role": "assistant", "content": "something harmful"}])
    assert result["messages"][-1].content == guardrails.CHAT_OUTPUT_REFUSAL
    assert all(m.content != "something harmful" for m in result["messages"])


async def test_orchestrator_chat_phase_replies_in_chat(monkeypatch):
    orch = Orchestrator(AsyncMock())
    orch.state = _chat_state()
    orch.state["messages"] = orch.state["messages"][:-1]
    orch.llm = AsyncMock()
    orch.llm.ainvoke.return_value = AIMessage(content="Bring a light jacket.")
    itinerary_graph = AsyncMock()
    orch.itinerary_graph = itinerary_graph
    assert not hasattr(orchestrator_module, "itinerary_node")

    await orch.process_message("What should I wear on day 1?")

    orch.broadcast.assert_any_await("agent_message", {"content": "Bring a light jacket."})
    itinerary_graph.ainvoke.assert_not_awaited()
    assert orch.state["itinerary"] == ITINERARY
    assert orch.state["messages"][-2].content == "What should I wear on day 1?"

