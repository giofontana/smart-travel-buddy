# AGENT.md

Guidance for AI coding agents working in this repository.

## What this is

Smart Travel Buddy is a demo app for Red Hat OpenShift AI: a conversational travel planner that produces a day-by-day itinerary. It showcases LangGraph agents, MCP tool servers, RAG on pgvector, MLflow tracing, containers + VMs on one platform, and GitOps with Argo CD. It is a demo, not a production service, so favor clarity and demo reliability over abstraction.

## Layout

| Path | Contents |
|------|----------|
| `backend/src/smart_travel_buddy/` | FastAPI app, LangGraph agent, RAG, WebSocket handler |
| `frontend/src/` | React 19 + Vite + Tailwind 4 UI |
| `mcp/{weather,currency,wikipedia}/` | Standalone FastMCP servers (SSE transport), each with its own `pyproject.toml` and tests |
| `knowledge/` | Markdown corpus for RAG (`destinations/`, `cultural/`, `packing/`) |
| `gitops/` | Kustomize base + overlays, Argo CD Applications |
| `docs/` | Demo narrative, design specs and implementation plans |
| `Makefile` | Entry point for build, run, test, lint, deploy |

## Request flow

1. The frontend opens a WebSocket at `/ws` (Vite proxies `/ws` and `/health` to `localhost:8000` in dev; `frontend/nginx.conf` does it in the container).
2. `ws/handler.py` accepts JSON actions: `start` (creates an `Orchestrator`), `message`, `cancel`. It rejects a new message while the previous one is still running. Outgoing events are `{"type": ..., **data}`.
3. `graph/orchestrator.py` holds one `TravelState` (`graph/state.py`) in memory per session and dispatches on `state["phase"]`:
   - **interview**: LangGraph subgraph (`graph/interview.py`, prompt in `prompts/interview.py`). The LLM signals completion by emitting a `{"ready"...}` JSON block, which the orchestrator strips before displaying the message and which flips the phase to `research`.
   - **research**: `graph/research.py`. Weather, currency and Wikipedia MCP calls run in parallel via `asyncio.gather`, then `call_rag` runs against pgvector. MCP tools are grouped into categories by substring matching on tool names in `_get_mcp_tools`, so renaming an MCP tool can silently drop it.
   - **itinerary**: `graph/itinerary.py` (prompt in `prompts/itinerary.py`) produces structured JSON rendered as day cards.
   - **refinement**: follow-up messages re-run `itinerary_node` against the existing state.
4. Broadcasts: research nodes call `broadcast({...})`, itinerary nodes call `broadcast("progress", {...})`. `_broadcast_wrapper` accepts both forms; keep that in mind when adding nodes.

Session state lives only in process memory (`MemorySaver` + `self.state`). Refreshing the browser starts a new session. The DB models in `models.py` exist, but conversations are not persisted by the orchestrator.

## Observability

- `trace.py` (`TraceEmitter`) streams start/end events over the WebSocket to the frontend flow overlay (`FlowOverlay.jsx`, `useTraceEvents.js`). Graph nodes take the emitter optionally from `config["configurable"]["trace"]`.
- `mlflow_utils.py` wraps each message in an MLflow run/span. It is a no-op unless `MLFLOW_TRACKING_URI` is set. The orchestrator records token usage and cost on the span (`LLM_INPUT_TOKEN_COST` / `LLM_OUTPUT_TOKEN_COST`, USD per 1M tokens) and separates `<think>...</think>` reasoning from the displayed answer.

## Configuration

Everything goes through `config.py` (pydantic-settings, reads `.env`). Key variables: `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` (any OpenAI-compatible endpoint; the demo uses Qwen served by vLLM on OpenShift AI), `OPENWEATHERMAP_API_KEY`, `DATABASE_URL` (asyncpg), `DATABASE_URL_SYNC` (psycopg, used by seed), `MCP_*_URL`, `MLFLOW_*`, `DEBUG`. Add new settings to `Settings` and to the backend Deployment env.

## Commands

```bash
make build                      # build all images (REGISTRY=quay.io/<org> TAG=latest)
make run / make stop / make clean   # local podman stack; frontend runs via `npm run dev` on :3000
make migrate                    # alembic upgrade head (run from host against localhost:5432)
make seed                       # embed knowledge/ into pgvector
make test                       # pytest for backend and each MCP server
make lint                       # ruff check + format --check (backend only, line length 120)
make deploy-container           # oc apply -k gitops/overlays/dev/container
make deploy-with-vm             # oc apply -k gitops/overlays/dev/mixed
```

Backend tests use `pytest-asyncio` in auto mode and an in-memory SQLite engine (`tests/conftest.py`), which needs `aiosqlite`. It is not listed in the `dev` extras, so install it separately. The frontend has no test or lint setup.

## Deployment (OpenShift)

- `gitops/base/` has one directory per component. PostgreSQL comes in two variants: `postgresql-container` (Deployment + PVC) and `postgresql-vm` (KubeVirt VirtualMachine + Service). Both expose the Service `postgresql`.
- Overlays: `overlays/dev/container` and `overlays/dev/mixed` both include `overlays/dev/shared` (SealedSecret for PostgreSQL, TLS edge Route, MLflow RoleBinding) and rewrite image names to `quay.io/gfontana/smart-travel-buddy-*`. `mixed` also sets `DEBUG=true` on the backend.
- Argo CD: `gitops/argocd/application-mixed.yaml` tracks `HEAD` of the GitHub repo with automated sync, prune and self-heal. **Anything pushed to the default branch deploys.** It ignores the VM's MAC address diff.
- **Not in git, must exist on the cluster:** the `backend-config` ConfigMap (`llm-model`, `llm-base-url`, optional `mlflow-*` keys) and the `api-keys` Secret (`llm-api-key`; `api-keys-secret.yaml` is gitignored). Do not commit plaintext secrets. Use SealedSecrets as `postgresql-secret.yaml` does.
- TLS: the backend's `build-ca-bundle` init container joins the `backend-trusted-ca` (cluster trusted CA) and `backend-service-ca` ConfigMaps into `/ca-bundle/ca-bundle.pem`, which is exposed as `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE`. This lets the backend reach in-cluster HTTPS services such as MLflow.
- The embedding model (sentence-transformers `all-MiniLM-L6-v2`) is downloaded at runtime. `HF_HOME=/tmp/hf_cache` in `backend/Containerfile` keeps the cache writable under OpenShift's random UID; preserve it.

## Conventions

- Python 3.12+, async throughout the backend. Graph nodes receive dependencies (`llm`, `broadcast`, `trace`, `mcp_tools`, `db_session`) through `config["configurable"]`, not globals.
- MCP servers are independent packages. Add tools there and keep the orchestrator's name-based categorization in sync.
- To add knowledge, drop a markdown file into the right `knowledge/` subfolder, run `make seed`, and add it to `gitops/base/backend/knowledge-configmap.yaml` (key format `<subfolder>--<file>.md`) so the cluster seed Job picks it up.
- Design specs and plans for past features live in `docs/superpowers/`. Follow that pattern for larger changes.

## Known inconsistencies

- The README references `make deploy` and `gitops/argocd/application.yaml`. The actual targets are `deploy-container` / `deploy-with-vm`, and the files are `application-container.yaml` / `application-mixed.yaml`.
- `docs/demo-narrative.md` starts the conversation with Paris but narrates Tokyo results (USD→JPY, Japanese etiquette) in the research and itinerary steps.
- `make help` still lists `make deploy`.
