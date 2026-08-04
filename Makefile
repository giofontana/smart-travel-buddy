REGISTRY ?= quay.io/your-org
TAG ?= latest
PODMAN ?= podman
NETWORK := smart-travel-buddy

IMAGES := backend frontend mcp-weather mcp-currency mcp-wikipedia

.PHONY: help build build-% push push-% run stop clean seed test lint deploy

help:
	@echo "Smart Travel Buddy"
	@echo ""
	@echo "Development:"
	@echo "  make run          - Run all services locally with podman"
	@echo "  make stop         - Stop all local containers"
	@echo "  make seed         - Seed the knowledge base into PostgreSQL"
	@echo "  make test         - Run all tests"
	@echo "  make lint         - Run linter"
	@echo ""
	@echo "Build:"
	@echo "  make build        - Build all container images"
	@echo "  make build-NAME   - Build a single image (backend, frontend, mcp-weather, mcp-currency, mcp-wikipedia)"
	@echo ""
	@echo "Push:"
	@echo "  make push         - Push all images to registry"
	@echo "  make push-NAME    - Push a single image"
	@echo ""
	@echo "Deploy:"
	@echo "  make deploy       - Apply Kustomize manifests to OpenShift"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove all local containers, network, and images"

# ── Build ────────────────────────────────────────────────────────

build: $(addprefix build-,$(IMAGES))

build-backend:
	$(PODMAN) build -t $(REGISTRY)/smart-travel-buddy-backend:$(TAG) -f backend/Containerfile backend/

build-frontend:
	$(PODMAN) build -t $(REGISTRY)/smart-travel-buddy-frontend:$(TAG) -f frontend/Containerfile frontend/

build-mcp-weather:
	$(PODMAN) build -t $(REGISTRY)/smart-travel-buddy-mcp-weather:$(TAG) -f mcp/weather/Containerfile mcp/weather/

build-mcp-currency:
	$(PODMAN) build -t $(REGISTRY)/smart-travel-buddy-mcp-currency:$(TAG) -f mcp/currency/Containerfile mcp/currency/

build-mcp-wikipedia:
	$(PODMAN) build -t $(REGISTRY)/smart-travel-buddy-mcp-wikipedia:$(TAG) -f mcp/wikipedia/Containerfile mcp/wikipedia/

# ── Push ─────────────────────────────────────────────────────────

push: $(addprefix push-,$(IMAGES))

push-%: build-%
	$(PODMAN) push $(REGISTRY)/smart-travel-buddy-$*:$(TAG)

# ── Run (local dev) ──────────────────────────────────────────────

run: _network run-db run-mcp-currency run-mcp-weather run-mcp-wikipedia run-backend run-frontend
	@echo ""
	@echo "All services running. Frontend at http://localhost:3000"
	@echo "Backend at http://localhost:8000"

_network:
	$(PODMAN) network create $(NETWORK) 2>/dev/null || true

run-db:
	$(PODMAN) run -d --name stb-postgresql --network $(NETWORK) \
		-e POSTGRES_DB=travel_agent_db \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-p 5432:5432 \
		pgvector/pgvector:pg16

run-mcp-currency:
	$(PODMAN) run -d --name stb-mcp-currency --network $(NETWORK) \
		-e FASTMCP_HOST=0.0.0.0 \
		-p 8002:8000 \
		$(REGISTRY)/smart-travel-buddy-mcp-currency:$(TAG)

run-mcp-weather:
	$(PODMAN) run -d --name stb-mcp-weather --network $(NETWORK) \
		--env-file .env \
		-e FASTMCP_HOST=0.0.0.0 \
		-p 8001:8000 \
		$(REGISTRY)/smart-travel-buddy-mcp-weather:$(TAG)

run-mcp-wikipedia:
	$(PODMAN) run -d --name stb-mcp-wikipedia --network $(NETWORK) \
		-e FASTMCP_HOST=0.0.0.0 \
		-p 8003:8000 \
		$(REGISTRY)/smart-travel-buddy-mcp-wikipedia:$(TAG)

run-backend:
	$(PODMAN) run -d --name stb-backend --network $(NETWORK) \
		--env-file .env \
		-e DATABASE_URL=postgresql+asyncpg://postgres:postgres@stb-postgresql:5432/travel_agent_db \
		-e DATABASE_URL_SYNC=postgresql+psycopg://postgres:postgres@stb-postgresql:5432/travel_agent_db \
		-e MCP_WEATHER_URL=http://stb-mcp-weather:8000/sse \
		-e MCP_CURRENCY_URL=http://stb-mcp-currency:8000/sse \
		-e MCP_WIKIPEDIA_URL=http://stb-mcp-wikipedia:8000/sse \
		-e DEBUG=true \
		-p 8000:8000 \
		$(REGISTRY)/smart-travel-buddy-backend:$(TAG)

run-frontend:
	@echo "Starting frontend dev server (not containerized for hot reload)..."
	cd frontend && npm run dev &

# ── Database ─────────────────────────────────────────────────────

migrate:
	cd backend && alembic -c alembic/alembic.ini upgrade head

seed:
	cd backend && python -m smart_travel_buddy.rag.seed ../knowledge

# ── Test & Lint ──────────────────────────────────────────────────

test:
	cd backend && python -m pytest tests/ -v
	cd mcp/currency && python -m pytest tests/ -v
	cd mcp/weather && python -m pytest tests/ -v
	cd mcp/wikipedia && python -m pytest tests/ -v

lint:
	cd backend && ruff check . && ruff format --check .

# ── Deploy ───────────────────────────────────────────────────────

deploy-container:
	oc apply -k gitops/overlays/dev/container/

deploy-with-vm:
	oc apply -k gitops/overlays/dev/mixed/

# ── Cleanup ──────────────────────────────────────────────────────

stop:
	$(PODMAN) stop stb-postgresql stb-mcp-currency stb-mcp-weather stb-mcp-wikipedia stb-backend 2>/dev/null || true
	$(PODMAN) rm stb-postgresql stb-mcp-currency stb-mcp-weather stb-mcp-wikipedia stb-backend 2>/dev/null || true

clean: stop
	$(PODMAN) network rm $(NETWORK) 2>/dev/null || true
	$(PODMAN) rmi $(addprefix $(REGISTRY)/smart-travel-buddy-,$(addsuffix :$(TAG),$(IMAGES))) 2>/dev/null || true
