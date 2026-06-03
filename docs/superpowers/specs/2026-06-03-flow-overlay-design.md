# Flow Overlay — Backend Visualization for Demo

Live animated flow diagram showing message flow through backend components during a Smart Travel Buddy session. Designed for demo presentations to make the agentic architecture visible in real time.

## Overview

A togglable overlay panel at the bottom of the app viewport that visualizes every backend interaction as an animated horizontal flow diagram. Components (User, Backend, LLM, MCP servers, RAG) are represented as boxes; animated dots travel between them as calls happen. A trace log and elapsed timer provide detailed timing data.

The overlay is driven by enriched WebSocket events from the existing broadcast infrastructure — no new connections or dependencies.

## Backend: Enriched Trace Events

### New event type

A `trace` event emitted at each transition point between backend components:

```json
{
  "type": "trace",
  "source": "backend",
  "target": "llm",
  "status": "started",
  "label": "Generating interview response",
  "timestamp": 1706000000.123,
  "request_id": "abc-123"
}
```

On completion:

```json
{
  "type": "trace",
  "source": "llm",
  "target": "backend",
  "status": "completed",
  "label": "Interview response received",
  "timestamp": 1706000002.456,
  "duration_ms": 2333,
  "request_id": "abc-123"
}
```

### Component identifiers

`user`, `backend`, `llm`, `mcp-weather`, `mcp-currency`, `mcp-wikipedia`, `rag`

### Trace points

Each interaction emits a `started`/`completed` pair:

**Interview phase:**
- `user → backend` — user message received
- `backend → llm` — LLM inference call
- `llm → backend` — LLM response received
- `backend → user` — agent message sent to frontend

**Research phase:**
- `backend → mcp-weather` — weather MCP call (parallel)
- `backend → mcp-currency` — currency MCP call (parallel)
- `backend → mcp-wikipedia` — wikipedia MCP call (parallel)
- `mcp-weather → backend` — weather result received
- `mcp-currency → backend` — currency result received
- `mcp-wikipedia → backend` — wikipedia result received
- `backend → rag` — RAG retrieval call (sequential, after MCP)
- `rag → backend` — RAG results received

**Itinerary phase:**
- `backend → llm` — itinerary generation call
- `llm → backend` — itinerary received
- `backend → user` — itinerary sent to frontend

### TraceEmitter class

New file: `smart_travel_buddy/trace.py`

Wraps the existing `broadcast` function. Provides:
- `start(source, target, label)` — emits a `trace` event with `status: "started"` and records the start time
- `end(source, target, label)` — emits a `trace` event with `status: "completed"`, calculates `duration_ms`
- Auto-generates `request_id` per user message to group related traces
- Auto-attaches `timestamp` (Unix epoch with millisecond precision)

Each research, interview, and itinerary function gets `trace.start()`/`trace.end()` calls at entry/exit points. Approximately 2-3 lines added per function.

### Backward compatibility

Existing `progress` events continue unchanged. The `trace` events are additive — the frontend's `ProgressCards` component is unaffected.

## Frontend: Flow Overlay

### New files

**`hooks/useTraceEvents.js`**
- Filters `trace` type messages from the existing `lastMessage` stream
- Maintains an array of trace events for the current request
- Derives: active connections (in-progress traces), completed connections, timing data
- Resets on each new user message

**`components/FlowOverlay.jsx`**
- Renders the animated horizontal flow diagram, trace log, and elapsed timer
- Receives trace state from `useTraceEvents` hook

Component layout (left to right within the overlay):

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Elapsed: 4.7s]                                                             │
│                                                                              │
│  ┌──────┐    ┌─────────┐    ┌─────┐    ┌─────────────┐    ┌──────┐  TRACE  │
│  │ 👤   │ ↔  │ ⚙️      │ ↔  │ 🧠  │    │ 🌤 Weather  │    │ 🗄️  │  LOG    │
│  │ User │    │ Backend │    │ LLM │ ↔  │ 💱 Currency │ ↔  │ RAG  │  ....   │
│  └──────┘    └─────────┘    └─────┘    │ 📚 Wikipedia│    └──────┘  ....   │
│                                        └─────────────┘                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

Component positions are fixed — they do not reorder between phases. Arrows animate between the relevant boxes for each phase:
- Interview: User ↔ Backend ↔ LLM (MCP and RAG stay idle)
- Research: Backend ↔ MCP servers (parallel), then Backend ↔ RAG (LLM idle)
- Itinerary: Backend ↔ LLM (MCP and RAG idle)

Visual states for each component box:
- **Idle** — gray/dim border, muted label
- **Source** — teal border, subtle glow (the component sending a request)
- **Active** — purple border, pulsing glow (the component currently processing)
- **Done** — green border, small checkmark badge

Connections:
- **Idle** — dim arrow
- **Active** — green arrow with animated dot traveling source → target
- **Done** — briefly highlighted green, then fades

Parallel calls: during research, three animated dots travel simultaneously from Backend to the three MCP servers.

**Trace log** (right side of overlay):
- Scrolling list of last ~8 trace events
- Format: `HH:MM:SS  Source → Target  duration`
- Green for completed, yellow/pulsing for in-progress
- Monospace font

**Elapsed timer** (top-right of overlay):
- Total time since user's message, updated live via `requestAnimationFrame` or 100ms interval
- Resets on each new user message

**`components/FlowToggle.jsx`**
- Floating circular button, bottom-right corner of viewport
- Uses `Activity` or `Network` icon from lucide-react
- Click toggles overlay open/closed
- Persists open/closed state in `localStorage`
- Positioned above the overlay when open

### Overlay panel styling

- Fixed position, anchored to bottom of viewport
- Full width, ~180-190px tall
- Background: `rgba(12, 12, 30, 0.96)` with `backdrop-filter: blur(8px)`
- Top border: subtle blue-ish line for separation
- Slide up/down animation on toggle (CSS transition or keyframe)
- Dark theme regardless of app theme — developer-console aesthetic

### Changes to existing files

**`App.jsx`** — add `useTraceEvents` hook call, render `FlowToggle` and `FlowOverlay`. ~5 lines.

No changes to: `ChatPanel`, `ProgressCards`, `ItineraryView`, `MessageBubble`, `useWebSocket`, or any other existing component.

## Scope

| Area | New files | Modified files |
|------|-----------|----------------|
| Backend | `trace.py` | `orchestrator.py`, `interview.py`, `research.py`, `itinerary.py` |
| Frontend | `useTraceEvents.js`, `FlowOverlay.jsx`, `FlowToggle.jsx` | `App.jsx` |
| Config/deploy | none | none |

No new dependencies. No changes to deployment manifests, Dockerfiles, or GitOps configuration.
