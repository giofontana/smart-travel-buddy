# Smart Travel Buddy

An AI-powered travel planning agent that creates personalized day-by-day itineraries through a conversational interface. Built with LangGraph, FastAPI, React, and MCP servers.

## How It Works

The agent follows a three-phase workflow:

1. **Interview** -- A conversational LLM collects travel details (destination, dates, interests, budget, constraints)
2. **Research** -- Three MCP tool servers fetch real-time weather forecasts, exchange rates, and destination info from Wikipedia. A RAG retriever searches a curated knowledge base for travel tips.
3. **Itinerary** -- The LLM synthesizes all research into a structured JSON itinerary rendered as interactive day cards in the browser.

Communication between frontend and backend happens over WebSocket, with live progress updates during the research phase.

## Architecture

```
┌──────────┐  WebSocket   ┌──────────────────────────────────────────┐
│ React UI ├─────────────►│ FastAPI Backend                          │
│ (Vite)   │◄─────────────┤                                          │
└──────────┘              │  ┌──────────────────────────────────────┐ │
                          │  │ LangGraph Orchestrator               │ │
                          │  │  ┌───────────┐ ┌──────────┐ ┌─────┐ │ │
                          │  │  │ Interview │►│ Research  │►│Itin.│ │ │
                          │  │  └───────────┘ └────┬─────┘ └─────┘ │ │
                          │  └─────────────────────┼───────────────┘ │
                          │                        │                 │
                          │  ┌─────────┬───────────┼──────────┐     │
                          │  │         │           │          │     │
                          │  ▼         ▼           ▼          ▼     │
                          │ MCP      MCP         MCP        RAG    │
                          │ Weather  Currency    Wikipedia  pgvector│
                          └──────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Tailwind CSS 4, Vite |
| Backend | FastAPI, Uvicorn, Python 3.12+ |
| Agent Framework | LangGraph, LangChain |
| LLM | Any OpenAI-compatible endpoint (configurable) |
| MCP Servers | FastMCP (SSE transport) |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Containers | Podman / Docker |
| Deployment | Kustomize, OpenShift |

## Project Structure

```
smart-travel-buddy/
├── backend/
│   ├── src/smart_travel_buddy/
│   │   ├── graph/          # LangGraph nodes (interview, research, itinerary, orchestrator)
│   │   ├── prompts/        # System prompts for each phase
│   │   ├── rag/            # Embeddings, retriever, seed script
│   │   ├── ws/             # WebSocket handler
│   │   ├── config.py       # Pydantic settings
│   │   ├── models.py       # SQLModel database models
│   │   └── server.py       # FastAPI app entry point
│   ├── alembic/            # Database migrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/     # ChatPanel, ItineraryView, ProgressCards
│   │   ├── hooks/          # useWebSocket
│   │   └── App.jsx         # Main two-panel layout
│   └── nginx.conf          # Reverse proxy config (WebSocket + static)
├── mcp/
│   ├── weather/            # OpenWeatherMap forecast & current weather
│   ├── currency/           # Frankfurter exchange rates & conversion
│   └── wikipedia/          # Wikipedia summaries & search
├── knowledge/              # Markdown files for RAG (destinations, cultural tips, packing)
├── gitops/
│   ├── base/               # Kubernetes manifests (deployments, services, PVCs)
│   └── overlays/dev/       # Dev overlay (secrets, configmap, routes, image registry)
└── Makefile                # Single entry point for all operations
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Podman (or Docker)
- An OpenAI-compatible LLM endpoint
- OpenWeatherMap API key ([get one here](https://openweathermap.org/api))

### 1. Configure environment

Create a `.env` file in the project root:

```env
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
OPENWEATHERMAP_API_KEY=your-key-here
```

### 2. Build container images

```bash
make build
```

### 3. Start all services

```bash
make run
```

This starts PostgreSQL (pgvector), three MCP servers, the backend, and the frontend dev server.

### 4. Run database migrations and seed the knowledge base

```bash
make migrate
make seed
```

### 5. Open the app

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

## Makefile Reference

| Command | Description |
|---------|-------------|
| `make run` | Start all services locally with Podman |
| `make stop` | Stop all local containers |
| `make build` | Build all container images |
| `make build-<name>` | Build a single image (`backend`, `frontend`, `mcp-weather`, `mcp-currency`, `mcp-wikipedia`) |
| `make push` | Push all images to registry |
| `make migrate` | Run Alembic database migrations |
| `make seed` | Seed the RAG knowledge base from `knowledge/` directory |
| `make test` | Run all test suites |
| `make lint` | Run ruff linter and formatter check |
| `make deploy` | Apply Kustomize manifests to OpenShift |
| `make clean` | Remove all containers, network, and images |

## Configuration

All settings are managed via environment variables (with `pydantic-settings`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODEL` | `gpt-4o` | Model name for the LLM |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API endpoint |
| `LLM_API_KEY` | -- | API key for the LLM |
| `OPENWEATHERMAP_API_KEY` | -- | OpenWeatherMap API key |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async database connection string |
| `DATABASE_URL_SYNC` | `postgresql+psycopg://...` | Sync database connection string (used by seed script) |
| `MCP_WEATHER_URL` | `http://localhost:8001/sse` | Weather MCP server SSE endpoint |
| `MCP_CURRENCY_URL` | `http://localhost:8002/sse` | Currency MCP server SSE endpoint |
| `MCP_WIKIPEDIA_URL` | `http://localhost:8003/sse` | Wikipedia MCP server SSE endpoint |

## MCP Servers

Each MCP server is a standalone FastMCP application exposing tools via SSE transport:

**Weather** (`mcp/weather/`) -- OpenWeatherMap API
- `get_forecast(city, country_code, days)` -- Multi-day forecast with daily aggregation
- `get_current_weather(city, country_code)` -- Current conditions

**Currency** (`mcp/currency/`) -- Frankfurter API (no auth required)
- `get_exchange_rate(from_currency, to_currency)` -- Current exchange rate
- `convert(amount, from_currency, to_currency)` -- Currency conversion

**Wikipedia** (`mcp/wikipedia/`) -- Wikipedia REST API
- `get_summary(topic)` -- Article summary with description and thumbnail
- `search(query, limit)` -- Search results with excerpts

## Knowledge Base

The `knowledge/` directory contains curated markdown files used for RAG retrieval:

- **Destinations** (10 cities): Bangkok, Barcelona, Cape Town, London, New York, Paris, Rio de Janeiro, Rome, Sydney, Tokyo
- **Cultural tips** (10 countries): etiquette, customs, and local norms
- **Packing guides** (4 types): beach, city-break, tropical, winter

Run `make seed` to embed and load these into pgvector.

## Deploying to OpenShift

The `gitops/` directory contains Kustomize manifests for OpenShift deployment:

```bash
# Apply the dev overlay
make deploy
# or manually:
oc apply -k gitops/overlays/dev/
```

The dev overlay configures:
- Container image registry (`quay.io/gfontana/`)
- PostgreSQL and API key secrets
- Backend ConfigMap (LLM endpoint configuration)
- Frontend Route with TLS edge termination
- DEBUG mode for the backend
