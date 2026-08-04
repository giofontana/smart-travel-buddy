# OpenShift AI Demonstration - Smart Travel Buddy

An AI-powered travel planning agent that creates personalized day-by-day itineraries through a conversational interface. Built with LangGraph, FastAPI, React, and MCP servers. Used for demonstration of OpenShift AI capabilities.

## How It Works

The agent follows a three-phase workflow:

1. **Interview** -- A conversational LLM collects travel details (destination, dates, interests, budget, constraints)
2. **Research** -- Three MCP tool servers fetch real-time weather forecasts, exchange rates, and destination info from Wikipedia. A RAG retriever searches a curated knowledge base for travel tips.
3. **Itinerary** -- The LLM synthesizes all research into a structured JSON itinerary rendered as interactive day cards in the browser.

Communication between frontend and backend happens over WebSocket, with live progress updates during the research phase.

## Architecture

```
┌──────────┐  WebSocket   ┌───────────────────────────────────────────────┐
│ React UI ├─────────────►│ FastAPI Backend                               │
│ (Vite)   │◄─────────────┤                                               │
└──────────┘              │  ┌──────────────────────────────────────────┐ │
                          │  │ LangGraph Orchestrator                   │ │
                          │  │  ┌───────────┐ ┌──────────┐ ┌──────────┐ │ │
                          │  │  │ Interview │►│ Research │►│Itinerary │ │ │
                          │  │  └───────────┘ └────┬─────┘ └──────────┘ │ │
                          │  └─────────────────────┼────────────────────┘ │
                          │                        │                      │
                          │  ┌─────────┬───────────┼──────────┐           │
                          │  │         │           │          │           │
                          │  ▼         ▼           ▼          ▼           │
                          │ MCP      MCP         MCP        RAG           │
                          │ Weather  Currency    Wikipedia  pgvector      │
                          └───────────────────────────────────────────────┘
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
- OpenWeatherMap API key -- sign up for a free account at [openweathermap.org](https://home.openweathermap.org/users/sign_up), then go to [API keys](https://home.openweathermap.org/api_keys) to generate a key

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

Note: Use `REGISTRY` variable to build the image in a custom registry. Example:

```bash
REGISTRY=quay.io/gfontana make build
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

First, create the API keys secret:

```bash
oc create secret generic api-keys \
  --from-literal=llm-api-key='your-llm-api-key' \
  --from-literal=openweathermap='your-openweathermap-api-key' \
  -n smart-travel-buddy
```

Then deploy:

```bash
# Apply the dev overlay. Postgresql will be deployed as a container
make deploy-container
# or the following to deploy Postgresql as a VM (OpenShift Virtualization required)
make deploy-with-vm

# or you may use the following to deploy manually:
oc apply -k gitops/overlays/dev/container # Postgresql as container
oc apply -k gitops/overlays/dev/mixed # Postgresql as VM

# or you may use ArgoCD:
oc apply -f gitops/argocd/application.yaml
```

The dev overlay configures:
- Container image registry (`quay.io/gfontana/`)
- PostgreSQL and API key secrets. Note that secret is using SealedSecrets
- Backend ConfigMap (LLM endpoint configuration)
- Frontend Route with TLS edge termination
- DEBUG mode for the backend

# Demo Narrative

**Duration:** ~20 minutes  
**Goal:** Show Smart Travel Buddy running live on OpenShift, highlighting agentic AI, MCP tools, RAG, and the unified container+VM platform.

## Pre-Demo Setup Checklist

- [ ] Application deployed
- [ ] OpenShift console open in a browser tab
- [ ] Smart Travel Buddy frontend open in a browser tab (fresh session, no prior conversation)
- [ ] OpenShift AI dashboard open showing the vLLM model serving endpoint (Qwen-14b-fp8)
- [ ] MLflow UI open in a tab (optional, for showing traces after)
- [ ] Terminal with `oc` CLI ready (for showing pods/VMs if needed)

---

## Act 1: Set the Stage (~3 min)

### Show the OpenShift Console

**Say:** "Before we start chatting with the agent, let me show you what's running behind the scenes."

1. **Switch to the OpenShift console.** Navigate to the project/namespace where Smart Travel Buddy is deployed.

2. **Show the running pods.** Point out:
   - `backend` pod -- the FastAPI backend with the LangGraph orchestrator
   - `frontend` pod -- the React UI, served by nginx
   - `mcp-weather`, `mcp-currency`, `mcp-wikipedia` pods -- the three MCP tool servers
   - The PostgreSQL VM (if using the VM overlay) -- highlight that this is a VirtualMachine, not a Pod

   **Say:** "Notice we have containers and a virtual machine running side by side on the same platform. The application services are containers, but the PostgreSQL database for our RAG knowledge base is running as a VM using OpenShift Virtualization. This is a single platform for all your workloads."

3. **Show the model serving endpoint in OpenShift AI.** Navigate to the OpenShift AI dashboard and show the vLLM InferenceService for Qwen-14b-fp8.

   **Say:** "Our LLM is Qwen 14-billion parameters, quantized to FP8 for efficiency. It's served by vLLM and managed by OpenShift AI using KServe. It exposes an OpenAI-compatible API, so any framework -- LangChain, LangGraph, or even a simple HTTP client -- can talk to it."

---

## Act 2: The Conversation (~7 min)

### Switch to the Smart Travel Buddy UI

**Say:** "Now let's plan a trip. I'll show you the three phases of the agent: interview, research, and itinerary generation."

### Phase 1: Interview

4. **Type the first message:**

   > "Paris"

   **Say:** "I'm starting a conversation with the agent. Right now we're in the Interview phase. The LangGraph orchestrator is running the interview subgraph, which uses the LLM to ask clarifying questions."

5. **Wait for the agent to respond.** It will ask about dates, interests, budget, etc.

   **Say:** "Notice the agent is asking follow-up questions -- it needs to know my dates, what I'm interested in, and my budget. This isn't a simple prompt-response. The agent has a structured state machine that tracks what information it has collected and what it still needs."

6. **Reply with dates:**

   > "Oct 1st to 5th"

7. **Reply with interests:**

   > "Arts and food"

8. **Reply with budget and constraints:**

   > "Mid-range. No special requirements."

   **Say:** "Once the agent has gathered enough information -- destination, dates, interests, budget -- it transitions to the Research phase automatically."

### Phase 2: Research

9. **Point out the progress cards** that appear on the right panel as research starts.

   **Say:** "Now watch the right panel. The agent is calling its external tools in parallel:"

   - "**Weather MCP** -- querying the OpenWeatherMap API for a 5-day forecast for Tokyo."
   - "**Currency MCP** -- fetching the USD to JPY exchange rate from the Frankfurter API."
   - "**Wikipedia MCP** -- pulling a summary about Tokyo from Wikipedia."
   - "**RAG** -- searching our curated knowledge base of destination guides, cultural tips, and packing lists using semantic search against pgvector."

   **Say:** "Each of these is a separate MCP server -- a containerized microservice that exposes tools via the Model Context Protocol. The weather, currency, and Wikipedia calls happen in parallel using asyncio. The RAG retrieval runs after, enriching the context with curated travel knowledge."

10. **Open MLflow interface**, toggle it open to show the trace visualization.

    **Say:** "This flow view shows the trace of the agent's actions -- you can see the messages flowing between the backend, each MCP server, and the RAG system."

### Phase 3: Itinerary

11. **Wait for the itinerary to render.** Day cards will appear on the right side with:
    - Day-by-day activities (morning, afternoon, evening)
    - Weather forecast per day (temperature, conditions)
    - Currency converter widget
    - Packing list with checkboxes
    - Cultural tips

    **Say:** "And here's the final itinerary. The LLM synthesized all the research data -- weather, exchange rates, Wikipedia info, and RAG knowledge -- into a structured, day-by-day plan. Each day has morning, afternoon, and evening activities, tailored to my interests in nature, culture, and food."

12. **Walk through the itinerary highlights:**

    - **Day cards:** "Each day shows activities with descriptions and practical tips."
    - **Weather:** "Real weather data for my travel dates -- so the agent planned outdoor activities for clear days."
    - **Currency:** "A live converter showing 1 USD equals approximately 150 JPY."
    - **Packing list:** "Generated based on the destination climate and trip type."
    - **Cultural tips:** "Japan-specific etiquette -- bowing, removing shoes, chopstick etiquette -- pulled from our RAG knowledge base."

---

## Act 3: Behind the Scenes (~3 min)

### Show the GitOps Manifests (optional, if time permits)

13. **Briefly show the Kustomize structure:**

    **Say:** "The entire application is deployed via GitOps. We have a base layer of Kubernetes manifests -- deployments, services, PVCs -- and a dev overlay that adds secrets, configmaps, routes, and image registry references. A single `oc apply -k` or ArgoCD sync deploys everything."

14. **Briefly show the Application on ArgoCD:**

    **Say:** "And here is the ArgoCD application, where you can see all application components, including the VM! All deployed and managed through ArgoCD. If someone by any reason makes a mistake, ArgoCD will detect it and revert to the desired state.

    - On OpenShift delete the backend-config ConfigMap and sync the ArgoCD app. Show that the CM is reverted back.

    **Say:** "As you can see, ArgoCD was able to detect the change and revert back to the desired state."

### Show MLflow (optional, if time permits)

14. **Switch to MLflow UI** and show the trace of the conversation:

    **Say:** "We also have MLflow integrated for experiment tracking and observability. Each conversation is logged as a run with traces for every LLM call and MCP tool invocation. You can see token usage, latency, and cost per interaction. This is critical for production -- you need to know how your agent is performing and how much it's costing."

### Wrap Up the Demo

15. **Switch back to the architecture slide (slide 29).**

    **Say:** "So to recap what you just saw: a conversational AI agent with a three-phase agentic workflow, powered by an LLM served by vLLM on OpenShift AI, calling external tools via MCP servers running as containers, enriched by a RAG knowledge base in a PostgreSQL VM -- all running on a single Red Hat OpenShift platform, deployed via GitOps."

---

## Demo Recovery Plan

**If the LLM is slow:** "The model is running inference on a single GPU -- in a production deployment you'd scale this horizontally with llm-d for distributed inference. Let me show you the architecture while we wait."

**If an MCP server fails:** "This is a live demo with real API calls. Let me show you the pod logs to diagnose." (`oc logs deployment/mcp-weather -n smart-travel-buddy`). The itinerary will still generate with partial data.

**If WebSocket disconnects:** Refresh the browser. The backend creates a new session automatically.

**If nothing works:** Switch to a pre-recorded video or screenshots (slide 27 has the app screenshot). "Let me walk you through a completed session instead."

---

## Key Talking Points to Weave In During Demo

- **MCP is the open standard** for connecting AI agents to tools. Each MCP server is a self-contained microservice with a defined interface. This is how agents interact with the real world.
- **LangGraph gives you control** over the agent flow. Unlike a simple chain, you get a state machine with explicit phases and transitions. The agent knows what it has collected and what it still needs.
- **RAG grounds the agent** in curated knowledge. The LLM's general knowledge is enriched with specific, verified travel information that you control.
- **Containers + VMs on one platform** is a real-world pattern. Databases, legacy systems, and appliances often run as VMs. OpenShift Virtualization means you don't need a separate infrastructure for them.
- **GitOps makes it reproducible.** The entire stack -- application, MCP servers, database, model serving -- is defined as code and deployed declaratively.
- **Observability is not optional.** MLflow traces every LLM call and tool invocation. In production, you need to know what your agent is doing, how long it takes, and how much it costs.
