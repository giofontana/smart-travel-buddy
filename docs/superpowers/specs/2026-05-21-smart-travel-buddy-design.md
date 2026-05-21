# Smart Travel Buddy — Design Spec

## Overview

Conversational AI agent that helps users plan trips. The user describes where and when they want to travel, the agent asks a few clarifying questions, then pulls live weather forecasts, currency exchange rates, and destination info via MCP servers, combines them with travel knowledge from a RAG store, and generates a rich visual day-by-day itinerary.

Built for demo purposes with a general/mixed audience — optimized for visual appeal and instant understandability.

## User Experience Flow

1. **Interview** — User states a destination and dates. The agent asks 2-3 follow-up questions one at a time: interests (culture, food, adventure, relaxation), budget level (budget/mid-range/luxury), constraints (dietary, accessibility). The LLM drives this naturally, not a rigid form.
2. **Research** — The agent fans out to 3 MCP servers in parallel. The frontend shows real-time progress cards animating in ("Checking weather for Tokyo...", "Converting USD to JPY...", "Researching Tokyo...").
3. **Itinerary** — A structured day-by-day plan rendered as rich cards: weather badges, activity lists with time-of-day tags, packing suggestions, cultural tips, currency reference.
4. **Refinement** — User can ask follow-ups: "make day 3 more food-focused", "what if it rains?", "add a day trip outside the city". The agent re-generates specific days without redoing all research.

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Frontend (React + Vite + Tailwind)    │
│  Chat panel  |  Itinerary cards  |  Side widgets│
│         WebSocket + REST to backend             │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│           Backend (FastAPI + LangGraph)          │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │          LangGraph State Machine           │  │
│  │                                            │  │
│  │  interview ──► research ──► itinerary ──►  │  │
│  │     (HiL)      (fan-out)    (generate)     │  │
│  │                    │                       │  │
│  │         ┌──────────┼──────────┐            │  │
│  │         ▼          ▼          ▼            │  │
│  │     Weather    Currency    Wikipedia       │  │
│  │      MCP        MCP         MCP           │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  RAG Engine  │  │  Session / History Store  │  │
│  │ (pgvector)   │  │     (PostgreSQL)          │  │
│  └──────────────┘  └──────────────────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│          PostgreSQL (pgvector extension)         │
│  - Chat sessions & history                       │
│  - RAG embeddings (travel guides, tips)          │
│  - Generated itineraries (JSONB)                 │
│  Connects via DATABASE_URL env var               │
└─────────────────────────────────────────────────┘
```

## LangGraph State Machine

Three subgraphs chained sequentially:

### Interview Subgraph

- Uses LangGraph's `interrupt()` for human-in-the-loop.
- Collects: destination, dates, interests, budget, constraints.
- The LLM drives the conversation naturally — transitions to research once it has enough info.

### Research Subgraph

- Fan-out pattern — calls all 3 MCPs in parallel:
  - Weather MCP: forecast for destination + dates.
  - Currency MCP: exchange rate from user's currency to destination currency.
  - Wikipedia MCP: destination overview, key landmarks, cultural context.
- RAG retrieval — queries pgvector for relevant travel guides, etiquette tips, packing checklists based on destination + season + interests.
- Aggregates all results into unified research context.
- Streams progress events to frontend via WebSocket.

### Itinerary Subgraph

- Receives the full research context.
- Generates a structured day-by-day itinerary as JSON so the frontend can render rich cards.
- Output schema:

```json
{
  "destination": "Tokyo, Japan",
  "dates": { "start": "2026-07-10", "end": "2026-07-14" },
  "currency": { "from": "USD", "to": "JPY", "rate": 149.5 },
  "packing": ["light rain jacket", "comfortable shoes"],
  "cultural_tips": ["Bow when greeting", "Remove shoes indoors"],
  "days": [
    {
      "date": "2026-07-10",
      "weather": {
        "temp_high": 31,
        "temp_low": 24,
        "condition": "Partly cloudy",
        "icon": "02d"
      },
      "activities": [
        {
          "name": "Senso-ji Temple",
          "time": "morning",
          "description": "Historic Buddhist temple in Asakusa",
          "tip": "Visit early to avoid crowds"
        }
      ]
    }
  ]
}
```

### Refinement Loop

- After itinerary is presented, the agent stays in a conversational loop.
- User can request changes; the agent re-generates specific days without redoing all research.

## MCP Servers

Each MCP runs as a standalone pod, communicating with the backend via SSE (Server-Sent Events) transport over HTTP. All use stable, free APIs.

### Weather MCP

- **API:** OpenWeatherMap — free tier, 1000 calls/day, API key required (free signup).
- **Tools:**
  - `get_forecast(city, country_code, days)` — daily forecast (temp high/low, condition, icon, humidity, wind).
  - `get_current_weather(city, country_code)` — current conditions.
- ~100 lines of Python.

### Currency MCP

- **API:** Frankfurter (frankfurter.app) — free, no API key, ECB data, updated daily.
- **Tools:**
  - `get_exchange_rate(from_currency, to_currency)` — latest rate.
  - `convert(amount, from_currency, to_currency)` — quick conversion.
- ~60 lines of Python.

### Wikipedia MCP

- **API:** Wikipedia REST API (en.wikipedia.org/api/rest_v1) — free, no key, very stable.
- **Tools:**
  - `get_summary(topic)` — extract + thumbnail for a topic.
  - `search(query, limit)` — search Wikipedia, return top matches with summaries.
- ~80 lines of Python.

### MCP Transport

- SSE over HTTP since MCPs are separate pods (not subprocesses).
- Each MCP runs a small HTTP server exposing the MCP protocol.
- Backend discovers MCPs via env vars: `MCP_WEATHER_URL`, `MCP_CURRENCY_URL`, `MCP_WIKIPEDIA_URL`.

## RAG Knowledge Base

### Content

Pre-loaded into pgvector via a seed script:

- **Destination guides** — 50-100 popular destinations: overview, best time to visit, neighborhoods, transportation, must-see spots.
- **Cultural etiquette** — greetings, tipping, dress codes, taboos per country/region.
- **Packing checklists** — templated by climate + trip type (beach, city, hiking, winter).
- **Food & dietary guides** — local cuisine highlights, dietary restriction navigation per destination.
- **Practical tips** — visa requirements, power adapters, connectivity, safety notes.

### Data Format

- Markdown files in a `knowledge/` directory, organized by destination.
- Chunked at ingestion (~500 tokens per chunk with overlap).
- Embedded using `all-MiniLM-L6-v2` via sentence-transformers — local, no external API.

### Retrieval

1. After interview determines destination + interests, a query is composed.
2. pgvector similarity search returns top-k relevant chunks.
3. Chunks injected into itinerary subgraph context alongside MCP results.

### Seeding

- `seed_knowledge.py` reads `knowledge/`, chunks, embeds, inserts into PostgreSQL.
- Runs as an init container or one-time Job in OpenShift.
- Idempotent — safe to re-run.

## Frontend

### Layout

Split-panel design:

- **Left panel** — Chat interface with message bubbles, typing indicator.
- **Right panel** — Dynamic content area:
  - During research: progress cards animate in.
  - After itinerary: card-based itinerary view.

### Thinking Mode

- Chat detects thinking tags in model responses (`<think>`, `<thinking>`, or similar).
- Renders thinking content as a collapsible "thinking" bubble with distinct styling (muted/italic, brain icon), separate from the final response.
- Works regardless of provider — bubble appears only when the model emits thinking tags.

### Itinerary View

- **Header card** — destination name, dates, currency rate badge, top cultural tip.
- **Day cards** — one per day: date + weather badge (icon, temp range), activity list with time-of-day tags, expandable tips.
- **Sidebar widgets** — packing checklist (toggleable checkboxes), cultural tips accordion, currency converter mini-widget.

### Tech

- React + Vite + Tailwind CSS + shadcn/ui.
- WebSocket for streaming chat + progress events.
- Responsive — works on projector screens and tablets/phones.
- No authentication (demo simplicity).
- Travel-themed color palette (blues, warm accents).
- Weather icons from OpenWeatherMap's built-in icon set.
- Smooth transitions/animations on card appearance.

## Database

### PostgreSQL + pgvector

Single database, single `DATABASE_URL` env var — works the same whether PostgreSQL runs in a container or on a VM.

### Schema

```
travel_agent_db
├── sessions          — id, created_at, destination, status
├── messages          — session_id, role, content, timestamp
├── knowledge_chunks  — id, source_file, chunk_text, embedding vector(384), metadata jsonb
└── itineraries       — session_id, itinerary_json (JSONB), version
```

- `knowledge_chunks.embedding` uses pgvector `vector(384)` (matches `all-MiniLM-L6-v2`).
- HNSW index on embedding column for fast similarity search.
- `itineraries` stores versions so refinements preserve the original.
- Schema managed via Alembic migrations.

## LLM Configuration

- Uses `ChatOpenAI` from `langchain-openai` — works with any OpenAI-compatible endpoint.
- No extra abstraction layer needed.

```
LLM_MODEL=gpt-4o                          # model name
LLM_BASE_URL=https://api.openai.com/v1    # OpenAI
LLM_BASE_URL=http://localhost:11434/v1     # Ollama
LLM_BASE_URL=http://vllm-host:8000/v1     # vLLM
LLM_API_KEY=sk-...                         # key (or "ollama" for local)
```

- Embedding model (`all-MiniLM-L6-v2`) runs locally inside the backend container via sentence-transformers — no external API dependency.

## Containerization & Deployment

### Pods (6 total)

| Pod | Image | Description |
|-----|-------|-------------|
| frontend | Node/nginx | React app, serves static build |
| backend | Python | FastAPI + LangGraph agent |
| mcp-weather | Python | OpenWeatherMap MCP server |
| mcp-currency | Python | Frankfurter MCP server |
| mcp-wikipedia | Python | Wikipedia REST MCP server |
| postgresql | pgvector/pgvector:pg16 | Database |

### Repository Structure

```
smart-travel-buddy/
├── frontend/              — React app + Containerfile
├── backend/               — FastAPI + LangGraph + Containerfile
├── mcp/
│   ├── weather/           — Weather MCP + Containerfile
│   ├── currency/          — Currency MCP + Containerfile
│   └── wikipedia/         — Wikipedia MCP + Containerfile
├── knowledge/             — RAG markdown files
├── gitops/
│   ├── base/
│   │   ├── frontend/
│   │   ├── backend/
│   │   ├── mcp-weather/
│   │   ├── mcp-currency/
│   │   ├── mcp-wikipedia/
│   │   └── postgresql/
│   └── overlays/
│       └── dev/
├── Makefile               — Build, run, deploy (single entry point, no docker-compose)
└── README.md
```

### GitOps

- Kustomize for manifests.
- Each component has its own folder under `gitops/base/`: Deployment, Service, ConfigMap/Secret refs.
- ArgoCD-ready — `gitops/` folder can be referenced from existing gitops infra.

### Makefile

Single entry point for all workflows:

- `make build` — build all container images.
- `make build-frontend`, `make build-backend`, `make build-mcp-weather`, etc. — build individual images.
- `make run` — run all containers locally via podman.
- `make stop` — stop local containers.
- `make seed` — run knowledge seeding script.
- `make deploy` — apply Kustomize manifests to OpenShift.
- `make clean` — remove local containers and images.

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | React, Vite, Tailwind CSS, shadcn/ui |
| Backend | Python, FastAPI, LangGraph, langchain-openai |
| MCP transport | SSE over HTTP |
| RAG embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Database | PostgreSQL 16 + pgvector |
| Schema migrations | Alembic |
| Container runtime | Podman |
| Orchestration | OpenShift / Kubernetes |
| GitOps | Kustomize + ArgoCD |
| Build/dev | Makefile |
