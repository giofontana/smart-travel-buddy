# Flow Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a togglable bottom overlay that animates message flow through backend components (User, Backend, LLM, MCP servers, RAG) in real time, with a trace log and elapsed timer.

**Architecture:** Enrich the existing WebSocket broadcast with `trace` events containing source, target, timestamp, and duration. A new React hook filters these events and drives a `FlowOverlay` component rendered as a fixed bottom panel. A floating toggle button shows/hides the overlay.

**Tech Stack:** Python (FastAPI backend, existing broadcast), React 19, Tailwind CSS, lucide-react icons, CSS animations.

---

## File Structure

### Backend (new)
- `backend/src/smart_travel_buddy/trace.py` — `TraceEmitter` class wrapping `broadcast` with timing

### Backend (modified)
- `backend/src/smart_travel_buddy/graph/orchestrator.py` — create `TraceEmitter`, pass to subgraphs, add `user↔backend` traces
- `backend/src/smart_travel_buddy/graph/interview.py` — add `backend↔llm` traces around LLM call
- `backend/src/smart_travel_buddy/graph/research.py` — add `backend↔mcp-*` and `backend↔rag` traces
- `backend/src/smart_travel_buddy/graph/itinerary.py` — add `backend↔llm` traces around LLM call

### Backend (test)
- `backend/tests/test_trace.py` — unit tests for `TraceEmitter`

### Frontend (new)
- `frontend/src/hooks/useTraceEvents.js` — hook to collect and derive state from trace events
- `frontend/src/components/FlowOverlay.jsx` — animated flow diagram, trace log, timer
- `frontend/src/components/FlowToggle.jsx` — floating toggle button

### Frontend (modified)
- `frontend/src/App.jsx` — wire up hook, render toggle and overlay

---

### Task 1: TraceEmitter class

**Files:**
- Create: `backend/src/smart_travel_buddy/trace.py`
- Test: `backend/tests/test_trace.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_trace.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/test_trace.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'smart_travel_buddy.trace'`

- [ ] **Step 3: Implement TraceEmitter**

Create `backend/src/smart_travel_buddy/trace.py`:

```python
import time
import uuid
from typing import Any, Callable, Coroutine

BroadcastFn = Callable[[str, dict], Coroutine[Any, Any, None]]


class TraceEmitter:
    def __init__(self, broadcast: BroadcastFn):
        self._broadcast = broadcast
        self._request_id = str(uuid.uuid4())[:8]
        self._starts: dict[str, float] = {}

    async def start(self, source: str, target: str, label: str):
        now = time.time()
        key = f"{source}->{target}"
        self._starts[key] = now
        await self._broadcast("trace", {
            "source": source,
            "target": target,
            "status": "started",
            "label": label,
            "timestamp": now,
            "request_id": self._request_id,
        })

    async def end(self, source: str, target: str, label: str):
        now = time.time()
        key = f"{target}->{source}"
        start_time = self._starts.pop(key, now)
        duration_ms = int((now - start_time) * 1000)
        await self._broadcast("trace", {
            "source": source,
            "target": target,
            "status": "completed",
            "label": label,
            "timestamp": now,
            "duration_ms": duration_ms,
            "request_id": self._request_id,
        })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/test_trace.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add backend/src/smart_travel_buddy/trace.py backend/tests/test_trace.py
git commit -m "feat: add TraceEmitter class for backend flow tracing"
```

---

### Task 2: Instrument orchestrator with trace events

**Files:**
- Modify: `backend/src/smart_travel_buddy/graph/orchestrator.py`

The orchestrator creates one `TraceEmitter` per `process_message` call and emits `user→backend` and `backend→user` traces. It also passes the emitter to subgraph functions via the config.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_trace.py`:

```python
@pytest.mark.asyncio
async def test_orchestrator_emits_user_backend_traces():
    """Verify orchestrator emits user→backend and backend→user trace events."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from langchain_core.messages import AIMessage

    trace_events = []
    async def capture_broadcast(event_type, data):
        if event_type == "trace":
            trace_events.append(data)

    from smart_travel_buddy.graph.orchestrator import Orchestrator
    orch = Orchestrator(capture_broadcast)
    orch.state["phase"] = "interview"

    mock_result = {
        "messages": [AIMessage(content="Where would you like to go?")],
        "phase": "interview",
    }
    with patch.object(orch.interview_graph, "ainvoke", new_callable=AsyncMock, return_value=mock_result):
        await orch.process_message("Hello")

    sources_targets = [(e["source"], e["target"]) for e in trace_events]
    assert ("user", "backend") in sources_targets
    assert ("backend", "user") in sources_targets
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/test_trace.py::test_orchestrator_emits_user_backend_traces -v`
Expected: FAIL — no `trace` events captured (orchestrator doesn't emit them yet)

- [ ] **Step 3: Modify orchestrator.py**

In `backend/src/smart_travel_buddy/graph/orchestrator.py`, make these changes:

Add import at the top:
```python
from smart_travel_buddy.trace import TraceEmitter
```

Modify `process_message` to create a `TraceEmitter` and emit `user→backend` at entry, `backend→user` at exit:

```python
async def process_message(self, user_message: str):
    self.state["messages"] = list(self.state["messages"]) + [HumanMessage(content=user_message)]
    trace = TraceEmitter(self.broadcast)

    await trace.start("user", "backend", f"Message received: {user_message[:50]}")

    if self.state["phase"] == "interview":
        await self._run_interview(trace)
    elif self.state["phase"] == "research":
        await self._run_research(trace)
        await self._run_itinerary(trace)
    elif self.state["phase"] == "refinement":
        await self._run_refinement(user_message, trace)

    await trace.end("backend", "user", "Response sent")
```

Update `_run_interview`, `_run_research`, `_run_itinerary`, and `_run_refinement` method signatures to accept `trace`:

```python
async def _run_interview(self, trace: TraceEmitter):
    config = {
        "configurable": {
            "llm": self.llm,
            "broadcast": self._broadcast_wrapper,
            "trace": trace,
            "thread_id": self.session_id,
        }
    }

    result = await self.interview_graph.ainvoke(self.state, config)
    self.state = {**self.state, **result}

    last_msg = self.state["messages"][-1]
    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    ready_idx = content.find('{"ready"')
    if ready_idx > 0:
        content = content[:ready_idx].rstrip()

    await self.broadcast("agent_message", {"content": content})

    if self.state["phase"] == "research":
        await self._run_research(trace)
        await self._run_itinerary(trace)

async def _run_research(self, trace: TraceEmitter):
    await self.broadcast("phase_change", {"phase": "research"})

    if not self.mcp_client:
        await self._init_mcp_client()

    config = {
        "configurable": {
            "mcp_tools": await self._get_mcp_tools(),
            "broadcast": self._broadcast_wrapper,
            "trace": trace,
            "db_session": None,
        }
    }

    import asyncio

    weather_result, currency_result, wikipedia_result = await asyncio.gather(
        call_weather(self.state, config),
        call_currency(self.state, config),
        call_wikipedia(self.state, config),
    )

    self.state["research_results"] = {
        **weather_result.get("research_results", {}),
        **currency_result.get("research_results", {}),
        **wikipedia_result.get("research_results", {}),
    }

    rag_result = await call_rag(self.state, config)
    self.state["research_results"]["rag_context"] = rag_result["research_results"].get("rag_context", "")

async def _run_itinerary(self, trace: TraceEmitter):
    config = {
        "configurable": {
            "llm": self.llm,
            "broadcast": self._broadcast_wrapper,
            "trace": trace,
        }
    }

    result = await self.itinerary_graph.ainvoke(self.state, config)
    self.state = {**self.state, **result}

async def _run_refinement(self, user_message: str, trace: TraceEmitter):
    config = {
        "configurable": {
            "llm": self.llm,
            "broadcast": self._broadcast_wrapper,
            "trace": trace,
        }
    }

    result = await itinerary_node(self.state, config)
    self.state = {**self.state, **result}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/test_trace.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Run existing tests to verify no regressions**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/ -v`
Expected: All existing tests PASS (interview, research, itinerary tests are unaffected — they pass `AsyncMock()` as broadcast, and the orchestrator tests use the new signature)

- [ ] **Step 6: Commit**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add backend/src/smart_travel_buddy/graph/orchestrator.py backend/tests/test_trace.py
git commit -m "feat: instrument orchestrator with trace events"
```

---

### Task 3: Instrument interview, research, and itinerary nodes

**Files:**
- Modify: `backend/src/smart_travel_buddy/graph/interview.py`
- Modify: `backend/src/smart_travel_buddy/graph/research.py`
- Modify: `backend/src/smart_travel_buddy/graph/itinerary.py`

Each node reads the `TraceEmitter` from config and emits `started`/`completed` pairs around its core work. The trace emitter is optional — if not present (e.g., in existing tests that pass `AsyncMock` as config), the node skips tracing.

- [ ] **Step 1: Write failing tests for interview tracing**

Add to `backend/tests/test_trace.py`:

```python
@pytest.mark.asyncio
async def test_interview_node_emits_llm_traces():
    """Verify interview_node emits backend→llm and llm→backend traces."""
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
```

- [ ] **Step 2: Write failing tests for research tracing**

Add to `backend/tests/test_trace.py`:

```python
@pytest.mark.asyncio
async def test_call_weather_emits_mcp_traces():
    """Verify call_weather emits backend→mcp-weather traces."""
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
```

- [ ] **Step 3: Write failing test for itinerary tracing**

Add to `backend/tests/test_trace.py`:

```python
@pytest.mark.asyncio
async def test_itinerary_node_emits_llm_traces():
    """Verify itinerary_node emits backend→llm and llm→backend traces."""
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
```

- [ ] **Step 4: Run all new tests to verify they fail**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/test_trace.py::test_interview_node_emits_llm_traces tests/test_trace.py::test_call_weather_emits_mcp_traces tests/test_trace.py::test_itinerary_node_emits_llm_traces -v`
Expected: All 3 FAIL — no trace events emitted yet

- [ ] **Step 5: Instrument interview_node**

In `backend/src/smart_travel_buddy/graph/interview.py`, modify `interview_node`:

```python
async def interview_node(state: TravelState, config: RunnableConfig) -> TravelState:
    llm = config["configurable"]["llm"]
    trace = config["configurable"].get("trace")

    messages = [SystemMessage(content=INTERVIEW_SYSTEM_PROMPT)] + state["messages"]

    if trace:
        await trace.start("backend", "llm", "Generating interview response")

    response = await llm.ainvoke(messages)

    if trace:
        await trace.end("llm", "backend", "Interview response received")

    state["messages"].append(response)
    state = extract_travel_info(state)

    return state
```

- [ ] **Step 6: Instrument research functions**

In `backend/src/smart_travel_buddy/graph/research.py`, modify each `call_*` function. The pattern is the same for all four — add trace calls around the tool invocation. Here is `call_weather` as the example; `call_currency`, `call_wikipedia`, and `call_rag` follow the same pattern with their respective component names (`mcp-currency`, `mcp-wikipedia`, `rag`):

```python
async def call_weather(state: TravelState, config: RunnableConfig) -> dict[str, Any]:
    destination = state["destination"]
    dates = state["dates"]

    broadcast = config["configurable"]["broadcast"]
    trace = config["configurable"].get("trace")

    await broadcast({
        "step": "weather",
        "status": "started",
        "label": f"Checking weather for {destination}..."
    })

    if trace:
        await trace.start("backend", "mcp-weather", f"Querying weather for {destination}")

    city, country_code = _extract_city(destination)

    if dates:
        start_date = datetime.strptime(dates["start"], "%Y-%m-%d")
        end_date = datetime.strptime(dates["end"], "%Y-%m-%d")
        days = (end_date - start_date).days + 1
    else:
        days = 7

    weather_tools = config["configurable"]["mcp_tools"]["weather"]
    weather_tool = None
    for tool in weather_tools:
        if "forecast" in tool.name.lower():
            weather_tool = tool
            break

    result = None
    if weather_tool:
        tool_input = {
            "city": city,
            "country_code": country_code,
            "days": days
        }
        result = await weather_tool.ainvoke(tool_input)

    if trace:
        await trace.end("mcp-weather", "backend", f"Weather data received for {destination}")

    await broadcast({
        "step": "weather",
        "status": "completed",
        "label": f"Weather data retrieved for {destination}"
    })

    return {
        "research_results": {
            **state["research_results"],
            "weather": result
        }
    }
```

For `call_currency`: use `"mcp-currency"` as component name, label `"Querying exchange rates"` / `"Exchange rates received"`.

For `call_wikipedia`: use `"mcp-wikipedia"` as component name, label `"Querying Wikipedia for {destination}"` / `"Wikipedia data received"`.

For `call_rag`: use `"rag"` as component name, label `"Searching knowledge base"` / `"Knowledge base results received"`.

- [ ] **Step 7: Instrument itinerary_node**

In `backend/src/smart_travel_buddy/graph/itinerary.py`, modify `itinerary_node`:

```python
async def itinerary_node(state: TravelState, config: RunnableConfig) -> TravelState:
    llm = config["configurable"]["llm"]
    broadcast = config["configurable"]["broadcast"]
    trace = config["configurable"].get("trace")

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

    if trace:
        await trace.start("backend", "llm", "Generating itinerary")

    response = await llm.ainvoke(messages)

    if trace:
        await trace.end("llm", "backend", "Itinerary generated")

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
```

- [ ] **Step 8: Run all tests**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/ -v`
Expected: All tests PASS — both new trace tests and existing tests (existing tests don't pass `trace` in config, so `config["configurable"].get("trace")` returns `None` and tracing is skipped)

- [ ] **Step 9: Commit**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add backend/src/smart_travel_buddy/graph/interview.py \
        backend/src/smart_travel_buddy/graph/research.py \
        backend/src/smart_travel_buddy/graph/itinerary.py \
        backend/tests/test_trace.py
git commit -m "feat: instrument interview, research, itinerary with trace events"
```

---

### Task 4: useTraceEvents hook

**Files:**
- Create: `frontend/src/hooks/useTraceEvents.js`

This hook filters `trace` events from the existing `lastMessage` prop and maintains derived state for the flow overlay.

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/useTraceEvents.js`:

```jsx
import { useState, useEffect, useRef, useCallback } from "react";

export function useTraceEvents(lastMessage) {
  const [events, setEvents] = useState([]);
  const [activeConnections, setActiveConnections] = useState([]);
  const [completedConnections, setCompletedConnections] = useState([]);
  const [startTime, setStartTime] = useState(null);
  const pendingStarts = useRef(new Map());

  const reset = useCallback(() => {
    setEvents([]);
    setActiveConnections([]);
    setCompletedConnections([]);
    setStartTime(Date.now());
    pendingStarts.current.clear();
  }, []);

  useEffect(() => {
    if (!lastMessage || lastMessage.type !== "trace") return;

    const evt = lastMessage;

    setEvents((prev) => [...prev].slice(-19).concat(evt));

    if (evt.status === "started") {
      if (!startTime) setStartTime(Date.now());
      const key = `${evt.source}->${evt.target}`;
      pendingStarts.current.set(key, evt.timestamp);
      setActiveConnections((prev) => [
        ...prev,
        { source: evt.source, target: evt.target, label: evt.label },
      ]);
    } else if (evt.status === "completed") {
      const key = `${evt.target}->${evt.source}`;
      pendingStarts.current.delete(key);
      setActiveConnections((prev) =>
        prev.filter(
          (c) => !(c.source === evt.target && c.target === evt.source)
        )
      );
      setCompletedConnections((prev) => [
        ...prev,
        {
          source: evt.source,
          target: evt.target,
          label: evt.label,
          duration_ms: evt.duration_ms,
        },
      ]);
    }
  }, [lastMessage, startTime]);

  return { events, activeConnections, completedConnections, startTime, reset };
}
```

- [ ] **Step 2: Commit**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add frontend/src/hooks/useTraceEvents.js
git commit -m "feat: add useTraceEvents hook for flow overlay state"
```

---

### Task 5: FlowToggle component

**Files:**
- Create: `frontend/src/components/FlowToggle.jsx`

- [ ] **Step 1: Create the toggle button**

Create `frontend/src/components/FlowToggle.jsx`:

```jsx
import { Activity } from "lucide-react";

export default function FlowToggle({ isOpen, onToggle }) {
  return (
    <button
      onClick={onToggle}
      title={isOpen ? "Hide flow diagram" : "Show flow diagram"}
      className="fixed z-[101] w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
      style={{
        bottom: isOpen ? "204px" : "20px",
        right: "20px",
        background: "rgba(12, 12, 30, 0.9)",
        border: "1px solid rgba(100, 100, 255, 0.25)",
        color: isOpen ? "#80cbc4" : "#666",
        boxShadow: "0 2px 12px rgba(0,0,0,0.3)",
      }}
    >
      <Activity size={18} />
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add frontend/src/components/FlowToggle.jsx
git commit -m "feat: add FlowToggle floating button component"
```

---

### Task 6: FlowOverlay component

**Files:**
- Create: `frontend/src/components/FlowOverlay.jsx`

This is the main visual component — the animated flow diagram, trace log, and elapsed timer.

- [ ] **Step 1: Create the FlowOverlay component**

Create `frontend/src/components/FlowOverlay.jsx`:

```jsx
import { useState, useEffect } from "react";

const COMPONENTS = [
  { id: "user", icon: "👤", label: "User" },
  { id: "backend", icon: "⚙️", label: "Backend" },
  { id: "llm", icon: "🧠", label: "LLM" },
  { id: "mcp-weather", icon: "🌤", label: "Weather" },
  { id: "mcp-currency", icon: "💱", label: "Currency" },
  { id: "mcp-wikipedia", icon: "📚", label: "Wikipedia" },
  { id: "rag", icon: "🗄️", label: "RAG" },
];

function ComponentBox({ id, icon, label, activeConnections, completedConnections }) {
  const isSource = activeConnections.some((c) => c.source === id);
  const isTarget = activeConnections.some((c) => c.target === id);
  const isDone = completedConnections.some(
    (c) => c.source === id || c.target === id
  );

  let stateClass = "comp-idle";
  if (isTarget) stateClass = "comp-active";
  else if (isSource) stateClass = "comp-source";
  else if (isDone) stateClass = "comp-done";

  return (
    <div className={`flow-comp ${stateClass}`}>
      <span className="flow-comp-icon">{icon}</span>
      <span className="flow-comp-label">{label}</span>
      {isDone && !isTarget && !isSource && (
        <span className="flow-comp-check">✓</span>
      )}
    </div>
  );
}

function Arrow({ from, to, activeConnections }) {
  const isActive = activeConnections.some(
    (c) => c.source === from && c.target === to
  );

  return (
    <div className={`flow-arrow ${isActive ? "flow-arrow-active" : ""}`}>
      <span>→</span>
      {isActive && <span className="flow-dot" />}
    </div>
  );
}

function McpArrows({ activeConnections }) {
  const targets = ["mcp-weather", "mcp-currency", "mcp-wikipedia"];
  const anyActive = targets.some((t) =>
    activeConnections.some((c) => c.source === "backend" && c.target === t)
  );

  return (
    <div className="flow-mcp-arrows">
      {targets.map((t) => {
        const isActive = activeConnections.some(
          (c) => c.source === "backend" && c.target === t
        );
        return (
          <div
            key={t}
            className={`flow-arrow flow-arrow-sm ${isActive ? "flow-arrow-active" : anyActive ? "" : "flow-arrow-dim"}`}
          >
            <span>→</span>
            {isActive && <span className="flow-dot" />}
          </div>
        );
      })}
    </div>
  );
}

function TraceLog({ events }) {
  const recent = events.slice(-8);

  return (
    <div className="flow-log">
      <div className="flow-log-title">Trace Log</div>
      {recent.map((evt, i) => {
        const time = new Date(evt.timestamp * 1000).toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
        const isCompleted = evt.status === "completed";

        return (
          <div
            key={i}
            className={`flow-log-entry ${isCompleted ? "flow-log-done" : "flow-log-active"}`}
          >
            <span className="flow-log-time">{time}</span>
            <span className="flow-log-detail">
              {evt.source} → {evt.target}
            </span>
            <span className="flow-log-duration">
              {isCompleted && evt.duration_ms != null
                ? evt.duration_ms >= 1000
                  ? `${(evt.duration_ms / 1000).toFixed(1)}s`
                  : `${evt.duration_ms}ms`
                : "..."}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ElapsedTimer({ startTime }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!startTime) return;
    const interval = setInterval(() => {
      setElapsed(((Date.now() - startTime) / 1000).toFixed(1));
    }, 100);
    return () => clearInterval(interval);
  }, [startTime]);

  if (!startTime) return null;

  return (
    <div className="flow-timer">
      <span className="flow-timer-label">Elapsed</span>
      <span className="flow-timer-value">{elapsed}s</span>
    </div>
  );
}

export default function FlowOverlay({
  isOpen,
  events,
  activeConnections,
  completedConnections,
  startTime,
}) {
  if (!isOpen) return null;

  return (
    <div className="flow-overlay">
      <ElapsedTimer startTime={startTime} />

      <div className="flow-diagram">
        {/* User */}
        <ComponentBox id="user" icon="👤" label="User"
          activeConnections={activeConnections} completedConnections={completedConnections} />

        <Arrow from="user" to="backend" activeConnections={activeConnections} />

        {/* Backend */}
        <ComponentBox id="backend" icon="⚙️" label="Backend"
          activeConnections={activeConnections} completedConnections={completedConnections} />

        <Arrow from="backend" to="llm" activeConnections={activeConnections} />

        {/* LLM */}
        <ComponentBox id="llm" icon="🧠" label="LLM"
          activeConnections={activeConnections} completedConnections={completedConnections} />

        {/* Parallel MCP arrows */}
        <McpArrows activeConnections={activeConnections} />

        {/* MCP group */}
        <div className="flow-mcp-group">
          <ComponentBox id="mcp-weather" icon="🌤" label="Weather"
            activeConnections={activeConnections} completedConnections={completedConnections} />
          <ComponentBox id="mcp-currency" icon="💱" label="Currency"
            activeConnections={activeConnections} completedConnections={completedConnections} />
          <ComponentBox id="mcp-wikipedia" icon="📚" label="Wikipedia"
            activeConnections={activeConnections} completedConnections={completedConnections} />
        </div>

        <Arrow from="backend" to="rag" activeConnections={activeConnections} />

        {/* RAG */}
        <ComponentBox id="rag" icon="🗄️" label="RAG"
          activeConnections={activeConnections} completedConnections={completedConnections} />
      </div>

      <TraceLog events={events} />
    </div>
  );
}
```

- [ ] **Step 2: Add CSS for FlowOverlay**

Append the following to `frontend/src/App.css` (the project's main CSS file that imports Tailwind):

```css
/* === Flow Overlay === */
.flow-overlay {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 190px;
  background: rgba(12, 12, 30, 0.96);
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(100, 100, 255, 0.15);
  display: flex;
  padding: 16px 24px;
  gap: 24px;
  z-index: 100;
  animation: flow-slideUp 0.3s ease-out;
}

@keyframes flow-slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.flow-diagram {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.flow-comp {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 14px;
  border-radius: 10px;
  min-width: 70px;
  position: relative;
  transition: all 0.3s ease;
}

.comp-idle {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.comp-idle .flow-comp-label { color: rgba(255, 255, 255, 0.4); }

.comp-active {
  background: rgba(106, 27, 154, 0.35);
  border: 1px solid #ce93d8;
  box-shadow: 0 0 18px rgba(206, 147, 216, 0.3);
}
.comp-active .flow-comp-label { color: #e1bee7; }

.comp-done {
  background: rgba(0, 150, 80, 0.2);
  border: 1px solid rgba(0, 200, 100, 0.4);
}
.comp-done .flow-comp-label { color: #81c784; }

.comp-source {
  background: rgba(0, 150, 150, 0.25);
  border: 1px solid rgba(0, 200, 200, 0.5);
}
.comp-source .flow-comp-label { color: #80cbc4; }

.flow-comp-icon { font-size: 22px; }
.flow-comp-label { font-size: 10px; font-weight: 500; letter-spacing: 0.3px; }

.flow-comp-check {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #43a047;
  color: #fff;
  font-size: 8px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.flow-arrow {
  display: flex;
  align-items: center;
  padding: 0 6px;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.15);
  position: relative;
  min-width: 30px;
  justify-content: center;
}
.flow-arrow-active { color: rgba(0, 255, 136, 0.6); }
.flow-arrow-dim { color: rgba(255, 255, 255, 0.08); }

.flow-arrow-sm {
  min-width: 24px;
  font-size: 14px;
  padding: 0 4px;
}

.flow-dot {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #00ff88;
  box-shadow: 0 0 8px #00ff88;
  animation: flow-travelRight 0.8s ease-in-out infinite;
}

@keyframes flow-travelRight {
  0% { left: 0; opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { left: calc(100% - 6px); opacity: 0; }
}

.flow-mcp-arrows {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
}

.flow-mcp-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.flow-mcp-group .flow-comp {
  min-width: 80px;
  padding: 6px 10px;
  flex-direction: row;
  gap: 6px;
}
.flow-mcp-group .flow-comp-icon { font-size: 14px; }
.flow-mcp-group .flow-comp-label { font-size: 8px; }

.flow-log {
  width: 260px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  padding-left: 20px;
  overflow-y: auto;
}

.flow-log-title {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.35);
  margin-bottom: 6px;
}

.flow-log-entry {
  font-size: 11px;
  font-family: "JetBrains Mono", "Fira Code", ui-monospace, monospace;
  padding: 3px 0;
  display: flex;
  gap: 8px;
  line-height: 1.3;
}

.flow-log-time { color: rgba(255, 255, 255, 0.3); min-width: 55px; }
.flow-log-detail { color: rgba(255, 255, 255, 0.7); flex: 1; }
.flow-log-duration { color: #81c784; font-size: 10px; }

.flow-log-active .flow-log-detail { color: #ffd54f; }
.flow-log-active .flow-log-duration { color: #ffd54f; }

.flow-timer {
  position: absolute;
  top: 12px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.flow-timer-label {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.flow-timer-value {
  font-size: 16px;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  color: #80cbc4;
  font-weight: 600;
}
```

- [ ] **Step 3: Commit**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add frontend/src/components/FlowOverlay.jsx frontend/src/App.css
git commit -m "feat: add FlowOverlay component with animated flow diagram"
```

---

### Task 7: Wire everything in App.jsx

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add imports, hook, and state**

In `frontend/src/App.jsx`, add imports at the top:

```jsx
import FlowOverlay from "./components/FlowOverlay";
import FlowToggle from "./components/FlowToggle";
import { useTraceEvents } from "./hooks/useTraceEvents";
```

Inside the `App` component, after the existing `useWebSocket` and state hooks, add:

```jsx
const [flowOpen, setFlowOpen] = useState(() => {
  try { return localStorage.getItem("flow-overlay") === "open"; } catch { return false; }
});
const traceState = useTraceEvents(lastMessage);
```

- [ ] **Step 2: Add toggle handler**

After the `handleSend` callback, add:

```jsx
const handleFlowToggle = useCallback(() => {
  setFlowOpen((prev) => {
    const next = !prev;
    try { localStorage.setItem("flow-overlay", next ? "open" : "closed"); } catch {}
    return next;
  });
}, []);
```

- [ ] **Step 3: Reset trace state on new message**

Inside the existing `handleSend` callback, add `traceState.reset()` at the beginning:

```jsx
const handleSend = useCallback(
  (content) => {
    traceState.reset();
    setMessages((prev) => [...prev, { role: "user", content }]);
    setIsProcessing(true);
    send({ action: "message", content });
  },
  [send, traceState]
);
```

- [ ] **Step 4: Render FlowToggle and FlowOverlay**

At the end of the return JSX, after the closing `</div>` of the main flex container but before the final `</div>`, add:

```jsx
<FlowToggle isOpen={flowOpen} onToggle={handleFlowToggle} />
<FlowOverlay
  isOpen={flowOpen}
  events={traceState.events}
  activeConnections={traceState.activeConnections}
  completedConnections={traceState.completedConnections}
  startTime={traceState.startTime}
/>
```

The full return statement should look like:

```jsx
return (
  <div className="h-screen flex">
    {/* Left panel: Chat */}
    <div className="w-[400px] min-w-[350px] border-r border-[var(--color-border)] bg-[var(--color-bg)]">
      <ChatPanel
        messages={messages}
        onSend={handleSend}
        isProcessing={isProcessing}
        connected={connected}
      />
    </div>

    {/* Right panel: Itinerary / Progress */}
    <div className="flex-1 bg-[var(--color-bg)] overflow-y-auto p-6">
      {phase === "research" && progress.length > 0 && !itinerary && (
        <ProgressCards progress={progress} />
      )}

      {itinerary && <ItineraryView itinerary={itinerary} />}

      {!itinerary && progress.length === 0 && (
        <div className="flex items-center justify-center h-full">
          <div className="text-center" style={{ color: "var(--color-text-muted)" }}>
            <p className="text-4xl mb-4">&#9992;&#65039;</p>
            <p className="text-lg font-medium">Your itinerary will appear here</p>
            <p className="text-sm mt-1">Start chatting to plan your trip</p>
          </div>
        </div>
      )}
    </div>

    <FlowToggle isOpen={flowOpen} onToggle={handleFlowToggle} />
    <FlowOverlay
      isOpen={flowOpen}
      events={traceState.events}
      activeConnections={traceState.activeConnections}
      completedConnections={traceState.completedConnections}
      startTime={traceState.startTime}
    />
  </div>
);
```

- [ ] **Step 5: Verify the frontend builds**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 6: Commit**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add frontend/src/App.jsx
git commit -m "feat: wire FlowOverlay and FlowToggle into App"
```

---

### Task 8: Manual verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/backend && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run frontend build**

Run: `cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Start the app and test visually**

Start the backend and frontend dev servers. Open the app in a browser:
1. Verify the floating toggle button (Activity icon) appears in the bottom-right corner
2. Click the toggle — the dark overlay should slide up from the bottom
3. All 7 component boxes should be visible in idle state (gray/dim)
4. Send a message in the chat — verify:
   - The elapsed timer starts counting
   - User and Backend boxes light up
   - During interview: animated dot travels User→Backend→LLM→Backend→User
   - The trace log populates with timestamps, source→target, and durations
5. When research starts:
   - Three animated dots travel in parallel to Weather, Currency, Wikipedia
   - Then RAG lights up
   - Then LLM lights up for itinerary generation
6. Click the toggle again — overlay should slide down and hide
7. Reload the page — the toggle state should persist (localStorage)

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
cd /gfontana/Dev/projects/personal/ai-ml/smart-travel-buddy
git add -A
git commit -m "fix: flow overlay adjustments from manual testing"
```
