from langchain_core.messages import AIMessage, HumanMessage
from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.graph.interview import should_continue_interview

def test_should_continue_interview_incomplete():
    state = TravelState(
        messages=[HumanMessage(content="I want to visit Tokyo"), AIMessage(content="Great! When?")],
        destination="", dates=None, interests=[], budget="", constraints=[],
        phase="interview", research_results={}, itinerary=None,
    )
    assert should_continue_interview(state) == "continue"

def test_should_continue_interview_complete():
    state = TravelState(
        messages=[
            HumanMessage(content="I want to visit Tokyo"),
            AIMessage(content='{"ready": true}'),
        ],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["food", "culture"], budget="mid-range", constraints=[],
        phase="interview", research_results={}, itinerary=None,
    )
    assert should_continue_interview(state) == "complete"
