import json
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.prompts.interview import INTERVIEW_SYSTEM_PROMPT


def should_continue_interview(state: TravelState) -> Literal["continue", "complete"]:
    """
    Determine if the interview should continue or is complete.

    Returns "complete" if:
    - All required fields (destination, dates, interests) are populated, OR
    - The last AI message contains a JSON block with {"ready": true}

    Otherwise returns "continue".
    """
    # Check if last message is from AI and contains ready signal
    if state["messages"]:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage):
            content = last_message.content
            if isinstance(content, str) and '{"ready": true' in content:
                return "complete"

    # Check if required fields are populated
    has_destination = bool(state.get("destination"))
    has_dates = state.get("dates") is not None
    has_interests = bool(state.get("interests"))

    if has_destination and has_dates and has_interests:
        return "complete"

    return "continue"


def extract_travel_info(state: TravelState) -> TravelState:
    """
    Extract travel information from the last AI message's JSON block.

    Looks for a JSON object with format:
    {"ready": true, "destination": "...", "dates": {...}, "interests": [...], "budget": "...", "constraints": [...]}

    Updates the state with extracted information and sets phase to "research".
    """
    if not state["messages"]:
        return state

    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        return state

    content = last_message.content
    if not isinstance(content, str):
        return state

    # Try to extract JSON block from the message
    idx = content.find('"ready"')
    if idx == -1:
        return state

    # Walk backwards to find the opening brace
    brace_idx = content.rfind("{", 0, idx)
    if brace_idx == -1:
        return state

    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(content, brace_idx)
    except (json.JSONDecodeError, ValueError):
        return state

    if data.get("ready"):
        if "destination" in data:
            state["destination"] = data["destination"]
        if "dates" in data:
            state["dates"] = data["dates"]
        if "interests" in data:
            state["interests"] = data["interests"]
        if "budget" in data:
            state["budget"] = data["budget"]
        if "constraints" in data:
            state["constraints"] = data["constraints"]

        state["phase"] = "research"

    return state


async def interview_node(state: TravelState, config: RunnableConfig) -> TravelState:
    """
    Interview node that conducts the conversation with the user.

    Expects config["configurable"]["llm"] to be a LangChain LLM instance.
    Prepends the system prompt, calls the LLM, appends the response,
    and extracts travel information if ready.
    """
    llm = config["configurable"]["llm"]

    # Prepend system prompt
    messages = [SystemMessage(content=INTERVIEW_SYSTEM_PROMPT)] + state["messages"]

    # Call LLM
    response = await llm.ainvoke(messages)

    # Append response to messages
    state["messages"].append(response)

    # Extract travel info if ready
    state = extract_travel_info(state)

    return state


def build_interview_graph() -> StateGraph:
    """
    Build the interview subgraph.

    Creates a graph with:
    - An "interview" node that conducts the conversation
    - Conditional edges based on should_continue_interview
    - Both "continue" and "complete" paths lead to END (for human-in-the-loop)
    """
    workflow = StateGraph(TravelState)

    # Add the interview node
    workflow.add_node("interview", interview_node)

    # Set entry point
    workflow.set_entry_point("interview")

    # Add conditional edges
    workflow.add_conditional_edges(
        "interview",
        should_continue_interview,
        {
            "continue": END,
            "complete": END,
        }
    )

    return workflow.compile()
