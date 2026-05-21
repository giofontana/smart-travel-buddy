# Smart Travel Buddy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a conversational AI travel agent that plans trips using live data from MCP servers (weather, currency, Wikipedia) and RAG knowledge, presented through a rich visual frontend.

**Architecture:** FastAPI backend with LangGraph state machine (interview → research → itinerary subgraphs). Three standalone MCP servers communicate via SSE. PostgreSQL + pgvector stores sessions, chat history, and RAG embeddings. React + Tailwind frontend with split-panel layout (chat + itinerary cards).

**Tech Stack:** Python 3.12, FastAPI, LangGraph, langchain-openai, langchain-mcp-adapters, sentence-transformers, PostgreSQL 16 + pgvector, Alembic, React 19, Vite, Tailwind CSS, shadcn/ui, Podman, Kustomize

---

## File Structure

```
smart-travel-buddy/
├── backend/
│   ├── src/smart_travel_buddy/
│   │   ├── __init__.py
│   │   ├── __main__.py              — uvicorn entry point
│   │   ├── server.py                — FastAPI app, CORS, WebSocket route, lifespan
│   │   ├── config.py                — pydantic-settings from env vars
│   │   ├── database.py              — async SQLAlchemy engine + session factory
│   │   ├── models.py                — SQLModel table definitions (sessions, messages, knowledge_chunks, itineraries)
│   │   ├── ws/
│   │   │   ├── __init__.py
│   │   │   └── handler.py           — WebSocket message handler (action dispatch, task management)
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── state.py             — TypedDict state definitions for all subgraphs
│   │   │   ├── interview.py         — interview subgraph (human-in-the-loop with interrupt())
│   │   │   ├── research.py          — research subgraph (fan-out MCP calls + RAG retrieval)
│   │   │   ├── itinerary.py         — itinerary subgraph (structured JSON generation)
│   │   │   └── orchestrator.py      — composes subgraphs into main graph, manages MCP clients
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── embeddings.py        — sentence-transformers wrapper (all-MiniLM-L6-v2)
│   │   │   ├── retriever.py         — pgvector similarity search
│   │   │   └── seed.py              — CLI script: reads knowledge/, chunks, embeds, inserts
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── interview.py         — interview system prompt
│   │       └── itinerary.py         — itinerary generation system prompt
│   ├── tests/
│   │   ├── conftest.py              — fixtures (async engine, mock LLM, test DB)
│   │   ├── test_config.py
│   │   ├── test_models.py
│   │   ├── test_rag.py
│   │   ├── test_graph_interview.py
│   │   ├── test_graph_research.py
│   │   └── test_graph_itinerary.py
│   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── pyproject.toml
│   └── Containerfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                  — top-level layout (split panel)
│   │   ├── App.css                  — global styles, travel-themed palette
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx        — chat input + message list
│   │   │   ├── MessageBubble.jsx    — user/assistant message rendering
│   │   │   ├── ThinkingBubble.jsx   — collapsible thinking content
│   │   │   ├── ItineraryView.jsx    — header card + day cards container
│   │   │   ├── DayCard.jsx          — single day: weather badge + activities
│   │   │   ├── WeatherBadge.jsx     — temp range + icon + condition
│   │   │   ├── ProgressCards.jsx    — animated research phase progress
│   │   │   ├── PackingChecklist.jsx — toggleable checklist widget
│   │   │   ├── CulturalTips.jsx     — accordion widget
│   │   │   ├── CurrencyConverter.jsx — mini converter widget
│   │   │   └── ui/                  — shadcn/ui components
│   │   ├── hooks/
│   │   │   └── useWebSocket.js      — WebSocket connection + auto-reconnect
│   │   └── lib/
│   │       └── utils.js             — Tailwind merge utility
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf                   — production reverse proxy config
│   └── Containerfile
├── mcp/
│   ├── currency/
│   │   ├── src/mcp_currency/
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py          — entry point: mcp.run(transport="sse")
│   │   │   └── server.py            — FastMCP tools: get_exchange_rate, convert
│   │   ├── tests/
│   │   │   └── test_server.py
│   │   ├── pyproject.toml
│   │   └── Containerfile
│   ├── weather/
│   │   ├── src/mcp_weather/
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py          — entry point: mcp.run(transport="sse")
│   │   │   └── server.py            — FastMCP tools: get_forecast, get_current_weather
│   │   ├── tests/
│   │   │   └── test_server.py
│   │   ├── pyproject.toml
│   │   └── Containerfile
│   └── wikipedia/
│       ├── src/mcp_wikipedia/
│       │   ├── __init__.py
│       │   ├── __main__.py          — entry point: mcp.run(transport="sse")
│       │   └── server.py            — FastMCP tools: get_summary, search
│       ├── tests/
│       │   └── test_server.py
│       ├── pyproject.toml
│       └── Containerfile
├── knowledge/
│   ├── destinations/
│   │   ├── tokyo.md
│   │   ├── paris.md
│   │   ├── new-york.md
│   │   ├── rome.md
│   │   ├── london.md
│   │   ├── barcelona.md
│   │   ├── bangkok.md
│   │   ├── sydney.md
│   │   ├── cape-town.md
│   │   └── rio-de-janeiro.md
│   ├── cultural/
│   │   ├── japan.md
│   │   ├── france.md
│   │   ├── usa.md
│   │   ├── italy.md
│   │   ├── uk.md
│   │   ├── spain.md
│   │   ├── thailand.md
│   │   ├── australia.md
│   │   ├── south-africa.md
│   │   └── brazil.md
│   └── packing/
│       ├── tropical.md
│       ├── winter.md
│       ├── city-break.md
│       └── beach.md
├── gitops/
│   ├── base/
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── frontend/
│   │   │   ├── kustomization.yaml
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   ├── backend/
│   │   │   ├── kustomization.yaml
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   ├── mcp-weather/
│   │   │   ├── kustomization.yaml
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   ├── mcp-currency/
│   │   │   ├── kustomization.yaml
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   ├── mcp-wikipedia/
│   │   │   ├── kustomization.yaml
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   └── postgresql/
│   │       ├── kustomization.yaml
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       └── pvc.yaml
│   └── overlays/
│       └── dev/
│           ├── kustomization.yaml
│           └── configmap.yaml
├── Makefile
├── .env.example
├── .gitignore
└── README.md
```

## Task Dependencies

```
Task 1 (Scaffolding)
├── Task 2 (Database) ──────────────────┐
│   ├── Task 6 (RAG Engine) ───────────┐│
│   └── Task 8 (Backend API) ──────────┤│
│       └── Task 9 (Interview) ────────┤│
├── Task 3 (Currency MCP) ─────────────┤│  ← Tasks 3,4,5 can run in parallel
├── Task 4 (Weather MCP) ──────────────┤│
├── Task 5 (Wikipedia MCP) ────────────┤│
│                                      ││
│       Task 10 (Research) ◄───────────┘│  ← depends on 3-5, 6, 9
│           └── Task 11 (Itinerary) ────┘  ← depends on 10
│
├── Task 7 (Knowledge Content) ◄── Task 6
├── Task 12 (Frontend Scaffold + Chat) ── independent of backend
│   └── Task 13 (Frontend Itinerary) ──── depends on 12
│
├── Task 14 (Containerfiles) ◄── all implementation tasks
├── Task 15 (GitOps) ◄── Task 14
└── Task 16 (Makefile) ◄── Task 15
```

---

### Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/smart_travel_buddy/__init__.py`
- Create: `backend/src/smart_travel_buddy/__main__.py`
- Create: `backend/src/smart_travel_buddy/config.py`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create backend pyproject.toml**

```toml
[project]
name = "smart-travel-buddy"
version = "0.1.0"
description = "AI-powered travel planning agent"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "langgraph>=0.4",
    "langchain-openai>=0.3",
    "langchain-mcp-adapters>=0.1",
    "langchain-core>=0.3",
    "sqlmodel>=0.0.22",
    "asyncpg>=0.30",
    "psycopg[binary]>=3.2",
    "pgvector>=0.3",
    "alembic>=1.14",
    "sentence-transformers>=3.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
]

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 120
```

- [ ] **Step 2: Create package init and entry point**

`backend/src/smart_travel_buddy/__init__.py`:
```python
```

`backend/src/smart_travel_buddy/__main__.py`:
```python
import uvicorn

from smart_travel_buddy.config import settings

uvicorn.run(
    "smart_travel_buddy.server:app",
    host="0.0.0.0",
    port=settings.port,
    reload=settings.debug,
)
```

- [ ] **Step 3: Create config module**

`backend/src/smart_travel_buddy/config.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    port: int = 8000

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/travel_agent_db"
    database_url_sync: str = "postgresql+psycopg://postgres:postgres@localhost:5432/travel_agent_db"

    llm_model: str = "gpt-4o"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = "sk-placeholder"

    mcp_weather_url: str = "http://localhost:8001/sse"
    mcp_currency_url: str = "http://localhost:8002/sse"
    mcp_wikipedia_url: str = "http://localhost:8003/sse"

    openweathermap_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 4: Create .env.example**

`.env.example`:
```bash
# LLM Configuration
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/travel_agent_db
DATABASE_URL_SYNC=postgresql+psycopg://postgres:postgres@localhost:5432/travel_agent_db

# MCP Server URLs
MCP_WEATHER_URL=http://localhost:8001/sse
MCP_CURRENCY_URL=http://localhost:8002/sse
MCP_WIKIPEDIA_URL=http://localhost:8003/sse

# API Keys
OPENWEATHERMAP_API_KEY=your-key-here

# App
DEBUG=true
PORT=8000
```

- [ ] **Step 5: Create .gitignore**

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
build/
.env
node_modules/
frontend/dist/
.ruff_cache/
.pytest_cache/
```

- [ ] **Step 6: Write config test**

`backend/tests/test_config.py`:
```python
from smart_travel_buddy.config import Settings


def test_default_settings():
    s = Settings(llm_api_key="test-key")
    assert s.port == 8000
    assert s.llm_model == "gpt-4o"
    assert s.mcp_weather_url == "http://localhost:8001/sse"
    assert s.mcp_currency_url == "http://localhost:8002/sse"
    assert s.mcp_wikipedia_url == "http://localhost:8003/sse"


def test_settings_override(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "llama3.1")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_API_KEY", "ollama")
    s = Settings()
    assert s.llm_model == "llama3.1"
    assert s.llm_base_url == "http://localhost:11434/v1"
```

- [ ] **Step 7: Install dependencies and run test**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_config.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git add backend/pyproject.toml backend/src/ backend/tests/test_config.py .env.example .gitignore
git commit -m "feat: project scaffolding with config and dependencies"
```

---

### Task 2: Database Models & Migrations

**Files:**
- Create: `backend/src/smart_travel_buddy/database.py`
- Create: `backend/src/smart_travel_buddy/models.py`
- Create: `backend/alembic/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/001_initial_schema.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write the model tests**

`backend/tests/conftest.py`:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from smart_travel_buddy.models import Session as ChatSession, Message, KnowledgeChunk, Itinerary


@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///test.db")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()
    import os
    os.remove("test.db") if os.path.exists("test.db") else None


@pytest.fixture
async def async_session(async_engine):
    async with AsyncSession(async_engine) as session:
        yield session
```

`backend/tests/test_models.py`:
```python
from smart_travel_buddy.models import Session as ChatSession, Message, Itinerary


async def test_create_session(async_session):
    session = ChatSession(destination="Tokyo, Japan", status="interview")
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    assert session.id is not None
    assert session.destination == "Tokyo, Japan"
    assert session.status == "interview"
    assert session.created_at is not None


async def test_create_message(async_session):
    session = ChatSession(destination="Paris, France", status="interview")
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)

    msg = Message(session_id=session.id, role="user", content="I want to visit Paris")
    async_session.add(msg)
    await async_session.commit()
    await async_session.refresh(msg)
    assert msg.id is not None
    assert msg.role == "user"
    assert msg.session_id == session.id


async def test_create_itinerary(async_session):
    session = ChatSession(destination="Rome, Italy", status="complete")
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)

    itinerary = Itinerary(
        session_id=session.id,
        itinerary_json={"destination": "Rome, Italy", "days": []},
        version=1,
    )
    async_session.add(itinerary)
    await async_session.commit()
    await async_session.refresh(itinerary)
    assert itinerary.id is not None
    assert itinerary.itinerary_json["destination"] == "Rome, Italy"
    assert itinerary.version == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate
pip install aiosqlite
pytest tests/test_models.py -v
```

Expected: FAIL — `models` module does not exist

- [ ] **Step 3: Create database module**

`backend/src/smart_travel_buddy/database.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from smart_travel_buddy.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 4: Create models**

`backend/src/smart_travel_buddy/models.py`:
```python
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: int | None = Field(default=None, primary_key=True)
    destination: str = ""
    status: str = "interview"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id")
    role: str
    content: str = Field(sa_column=Column(Text))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeChunk(SQLModel, table=True):
    __tablename__ = "knowledge_chunks"

    id: int | None = Field(default=None, primary_key=True)
    source_file: str
    chunk_text: str = Field(sa_column=Column(Text))
    metadata_: dict[str, Any] = Field(default={}, sa_column=Column("metadata", JSONB, default={}))
    # embedding column added via Alembic migration (pgvector Vector(384))
    # not in SQLModel because sqlite tests don't support pgvector


class Itinerary(SQLModel, table=True):
    __tablename__ = "itineraries"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id")
    itinerary_json: dict[str, Any] = Field(default={}, sa_column=Column(JSONB, default={}))
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_models.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 6: Create Alembic configuration**

`backend/alembic/alembic.ini`:
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+psycopg://postgres:postgres@localhost:5432/travel_agent_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

`backend/alembic/env.py`:
```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from smart_travel_buddy.models import Session, Message, KnowledgeChunk, Itinerary

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Create initial migration**

`backend/alembic/versions/001_initial_schema.py`:
```python
"""Initial schema with pgvector

Revision ID: 001
Revises:
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("destination", sa.String, default=""),
        sa.Column("status", sa.String, default="interview"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("source_file", sa.String, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(384)),
        sa.Column("metadata", sa.dialects.postgresql.JSONB, default={}),
    )
    op.create_index(
        "ix_knowledge_chunks_embedding",
        "knowledge_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "itineraries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("itinerary_json", sa.dialects.postgresql.JSONB, default={}),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("itineraries")
    op.drop_table("knowledge_chunks")
    op.drop_table("messages")
    op.drop_table("sessions")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

- [ ] **Step 8: Commit**

```bash
git add backend/src/smart_travel_buddy/database.py backend/src/smart_travel_buddy/models.py \
       backend/alembic/ backend/tests/conftest.py backend/tests/test_models.py
git commit -m "feat: database models and Alembic migrations with pgvector"
```

---

### Task 3: Currency MCP Server

**Files:**
- Create: `mcp/currency/pyproject.toml`
- Create: `mcp/currency/src/mcp_currency/__init__.py`
- Create: `mcp/currency/src/mcp_currency/__main__.py`
- Create: `mcp/currency/src/mcp_currency/server.py`
- Create: `mcp/currency/tests/test_server.py`

**Independent:** Can run in parallel with Tasks 4 and 5.

- [ ] **Step 1: Write the MCP server test**

`mcp/currency/tests/test_server.py`:
```python
from unittest.mock import AsyncMock, patch

import pytest

from mcp_currency.server import get_exchange_rate, convert


@pytest.fixture
def mock_frankfurter_rate():
    return {"base": "USD", "date": "2026-05-21", "rates": {"JPY": 149.5}}


@pytest.fixture
def mock_frankfurter_convert():
    return {"base": "USD", "date": "2026-05-21", "rates": {"JPY": 149.5}, "amount": 100}


@pytest.mark.asyncio
async def test_get_exchange_rate(mock_frankfurter_rate):
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_frankfurter_rate
    mock_response.raise_for_status = lambda: None

    with patch("mcp_currency.server.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await get_exchange_rate("USD", "JPY")
        assert "149.5" in result
        assert "USD" in result
        assert "JPY" in result


@pytest.mark.asyncio
async def test_convert(mock_frankfurter_convert):
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_frankfurter_convert
    mock_response.raise_for_status = lambda: None

    with patch("mcp_currency.server.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await convert(100.0, "USD", "JPY")
        assert "14950" in result or "149.5" in result
        assert "USD" in result
```

- [ ] **Step 2: Create pyproject.toml**

`mcp/currency/pyproject.toml`:
```toml
[project]
name = "mcp-currency"
version = "0.1.0"
description = "MCP server for currency exchange rates via Frankfurter API"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd mcp/currency
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_server.py -v
```

Expected: FAIL — `mcp_currency.server` does not exist

- [ ] **Step 4: Implement the currency MCP server**

`mcp/currency/src/mcp_currency/__init__.py`:
```python
```

`mcp/currency/src/mcp_currency/server.py`:
```python
import json

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("currency")

FRANKFURTER_BASE = "https://api.frankfurter.app"


@mcp.tool()
async def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """Get the latest exchange rate between two currencies. Uses ECB reference rates updated daily."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{FRANKFURTER_BASE}/latest", params={"from": from_currency, "to": to_currency})
        resp.raise_for_status()
        data = resp.json()
        rate = data["rates"][to_currency]
        return json.dumps({"from": from_currency, "to": to_currency, "rate": rate, "date": data["date"]})


@mcp.tool()
async def convert(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount from one currency to another using latest ECB exchange rates."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{FRANKFURTER_BASE}/latest", params={"amount": amount, "from": from_currency, "to": to_currency}
        )
        resp.raise_for_status()
        data = resp.json()
        converted = data["rates"][to_currency]
        return json.dumps({
            "amount": amount,
            "from": from_currency,
            "to": to_currency,
            "converted": converted,
            "rate": converted / amount,
            "date": data["date"],
        })
```

`mcp/currency/src/mcp_currency/__main__.py`:
```python
from mcp_currency.server import mcp

mcp.run(transport="sse")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd mcp/currency && source .venv/bin/activate
pytest tests/test_server.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add mcp/currency/
git commit -m "feat: currency MCP server wrapping Frankfurter API"
```

---

### Task 4: Weather MCP Server

**Files:**
- Create: `mcp/weather/pyproject.toml`
- Create: `mcp/weather/src/mcp_weather/__init__.py`
- Create: `mcp/weather/src/mcp_weather/__main__.py`
- Create: `mcp/weather/src/mcp_weather/server.py`
- Create: `mcp/weather/tests/test_server.py`

**Independent:** Can run in parallel with Tasks 3 and 5.

- [ ] **Step 1: Write the MCP server test**

`mcp/weather/tests/test_server.py`:
```python
from unittest.mock import AsyncMock, patch

import pytest

from mcp_weather.server import get_forecast, get_current_weather


@pytest.fixture
def mock_forecast_response():
    return {
        "city": {"name": "Tokyo", "country": "JP"},
        "list": [
            {
                "dt": 1720600800,
                "main": {"temp_min": 24.0, "temp_max": 31.0, "humidity": 70},
                "weather": [{"main": "Clouds", "description": "partly cloudy", "icon": "02d"}],
                "wind": {"speed": 3.5},
            }
        ],
    }


@pytest.fixture
def mock_current_response():
    return {
        "name": "Tokyo",
        "sys": {"country": "JP"},
        "main": {"temp": 28.5, "humidity": 65},
        "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
        "wind": {"speed": 2.1},
    }


@pytest.mark.asyncio
async def test_get_forecast(mock_forecast_response):
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_forecast_response
    mock_response.raise_for_status = lambda: None

    with patch("mcp_weather.server.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await get_forecast("Tokyo", "JP", 5)
        assert "Tokyo" in result
        assert "partly cloudy" in result or "temp_max" in result


@pytest.mark.asyncio
async def test_get_current_weather(mock_current_response):
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_current_response
    mock_response.raise_for_status = lambda: None

    with patch("mcp_weather.server.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await get_current_weather("Tokyo", "JP")
        assert "Tokyo" in result
        assert "28.5" in result or "clear" in result
```

- [ ] **Step 2: Create pyproject.toml**

`mcp/weather/pyproject.toml`:
```toml
[project]
name = "mcp-weather"
version = "0.1.0"
description = "MCP server for weather forecasts via OpenWeatherMap API"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd mcp/weather
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_server.py -v
```

Expected: FAIL — `mcp_weather.server` does not exist

- [ ] **Step 4: Implement the weather MCP server**

`mcp/weather/src/mcp_weather/__init__.py`:
```python
```

`mcp/weather/src/mcp_weather/server.py`:
```python
import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

OWM_BASE = "https://api.openweathermap.org/data/2.5"


def _get_api_key() -> str:
    key = os.environ.get("OPENWEATHERMAP_API_KEY", "")
    if not key:
        raise ValueError("OPENWEATHERMAP_API_KEY environment variable is required")
    return key


@mcp.tool()
async def get_forecast(city: str, country_code: str, days: int = 5) -> str:
    """Get weather forecast for a city. Returns daily forecast with temperature, conditions, humidity, and wind."""
    api_key = _get_api_key()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OWM_BASE}/forecast",
            params={"q": f"{city},{country_code}", "appid": api_key, "units": "metric", "cnt": days * 8},
        )
        resp.raise_for_status()
        data = resp.json()

    daily = {}
    for item in data["list"]:
        from datetime import datetime

        date = datetime.fromtimestamp(item["dt"]).strftime("%Y-%m-%d")
        if date not in daily:
            daily[date] = {
                "date": date,
                "temp_min": item["main"]["temp_min"],
                "temp_max": item["main"]["temp_max"],
                "humidity": item["main"]["humidity"],
                "condition": item["weather"][0]["description"],
                "icon": item["weather"][0]["icon"],
                "wind_speed": item["wind"]["speed"],
            }
        else:
            daily[date]["temp_min"] = min(daily[date]["temp_min"], item["main"]["temp_min"])
            daily[date]["temp_max"] = max(daily[date]["temp_max"], item["main"]["temp_max"])

    result = {"city": data["city"]["name"], "country": data["city"]["country"], "forecast": list(daily.values())[:days]}
    return json.dumps(result)


@mcp.tool()
async def get_current_weather(city: str, country_code: str) -> str:
    """Get current weather conditions for a city."""
    api_key = _get_api_key()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OWM_BASE}/weather",
            params={"q": f"{city},{country_code}", "appid": api_key, "units": "metric"},
        )
        resp.raise_for_status()
        data = resp.json()

    result = {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "condition": data["weather"][0]["description"],
        "icon": data["weather"][0]["icon"],
        "wind_speed": data["wind"]["speed"],
    }
    return json.dumps(result)
```

`mcp/weather/src/mcp_weather/__main__.py`:
```python
from mcp_weather.server import mcp

mcp.run(transport="sse")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd mcp/weather && source .venv/bin/activate
pytest tests/test_server.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add mcp/weather/
git commit -m "feat: weather MCP server wrapping OpenWeatherMap API"
```

---

### Task 5: Wikipedia MCP Server

**Files:**
- Create: `mcp/wikipedia/pyproject.toml`
- Create: `mcp/wikipedia/src/mcp_wikipedia/__init__.py`
- Create: `mcp/wikipedia/src/mcp_wikipedia/__main__.py`
- Create: `mcp/wikipedia/src/mcp_wikipedia/server.py`
- Create: `mcp/wikipedia/tests/test_server.py`

**Independent:** Can run in parallel with Tasks 3 and 4.

- [ ] **Step 1: Write the MCP server test**

`mcp/wikipedia/tests/test_server.py`:
```python
from unittest.mock import AsyncMock, patch

import pytest

from mcp_wikipedia.server import get_summary, search


@pytest.fixture
def mock_summary_response():
    return {
        "title": "Tokyo",
        "extract": "Tokyo is the capital of Japan and one of the most populous cities in the world.",
        "thumbnail": {"source": "https://upload.wikimedia.org/thumb/tokyo.jpg"},
        "description": "Capital city of Japan",
    }


@pytest.fixture
def mock_search_response():
    return {
        "pages": [
            {"title": "Tokyo", "excerpt": "Capital of Japan", "thumbnail": None},
            {"title": "Tokyo Tower", "excerpt": "Communications tower in Tokyo", "thumbnail": None},
        ]
    }


@pytest.mark.asyncio
async def test_get_summary(mock_summary_response):
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_summary_response
    mock_response.raise_for_status = lambda: None

    with patch("mcp_wikipedia.server.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await get_summary("Tokyo")
        assert "Tokyo" in result
        assert "capital" in result.lower()


@pytest.mark.asyncio
async def test_search(mock_search_response):
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_search_response
    mock_response.raise_for_status = lambda: None

    with patch("mcp_wikipedia.server.httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        client_instance.get.return_value = mock_response
        client_instance.__aenter__ = AsyncMock(return_value=client_instance)
        client_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = client_instance

        result = await search("Tokyo landmarks", 5)
        assert "Tokyo" in result
```

- [ ] **Step 2: Create pyproject.toml**

`mcp/wikipedia/pyproject.toml`:
```toml
[project]
name = "mcp-wikipedia"
version = "0.1.0"
description = "MCP server for Wikipedia article summaries and search"
requires-python = ">=3.12"
dependencies = [
    "mcp>=1.0",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd mcp/wikipedia
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_server.py -v
```

Expected: FAIL — `mcp_wikipedia.server` does not exist

- [ ] **Step 4: Implement the Wikipedia MCP server**

`mcp/wikipedia/src/mcp_wikipedia/__init__.py`:
```python
```

`mcp/wikipedia/src/mcp_wikipedia/server.py`:
```python
import json

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("wikipedia")

WIKI_BASE = "https://en.wikipedia.org/api/rest_v1"
WIKI_SEARCH_BASE = "https://en.wikipedia.org/w/rest.php/v1"


@mcp.tool()
async def get_summary(topic: str) -> str:
    """Get a summary of a Wikipedia article including extract and thumbnail image URL."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{WIKI_BASE}/page/summary/{topic}",
            headers={"User-Agent": "SmartTravelBuddy/1.0"},
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()

    result = {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "extract": data.get("extract", ""),
        "thumbnail": data.get("thumbnail", {}).get("source", ""),
    }
    return json.dumps(result)


@mcp.tool()
async def search(query: str, limit: int = 5) -> str:
    """Search Wikipedia and return top matching articles with titles and excerpts."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{WIKI_SEARCH_BASE}/search/page",
            params={"q": query, "limit": limit},
            headers={"User-Agent": "SmartTravelBuddy/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for page in data.get("pages", []):
        results.append({
            "title": page.get("title", ""),
            "excerpt": page.get("excerpt", "").replace('<span class="searchmatch">', "").replace("</span>", ""),
            "thumbnail": page.get("thumbnail", {}).get("url", "") if page.get("thumbnail") else "",
        })
    return json.dumps({"query": query, "results": results})
```

`mcp/wikipedia/src/mcp_wikipedia/__main__.py`:
```python
from mcp_wikipedia.server import mcp

mcp.run(transport="sse")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd mcp/wikipedia && source .venv/bin/activate
pytest tests/test_server.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add mcp/wikipedia/
git commit -m "feat: Wikipedia MCP server wrapping REST API"
```

---

### Task 6: RAG Engine & Knowledge Seeding

**Files:**
- Create: `backend/src/smart_travel_buddy/rag/__init__.py`
- Create: `backend/src/smart_travel_buddy/rag/embeddings.py`
- Create: `backend/src/smart_travel_buddy/rag/retriever.py`
- Create: `backend/src/smart_travel_buddy/rag/seed.py`
- Create: `backend/tests/test_rag.py`

**Depends on:** Task 2 (database models)

- [ ] **Step 1: Write RAG tests**

`backend/tests/test_rag.py`:
```python
from smart_travel_buddy.rag.embeddings import EmbeddingModel


def test_embedding_model_loads():
    model = EmbeddingModel()
    assert model.dimension == 384


def test_embedding_model_encodes():
    model = EmbeddingModel()
    embedding = model.encode("Tokyo is the capital of Japan")
    assert len(embedding) == 384
    assert isinstance(embedding[0], float)


def test_embedding_model_batch():
    model = EmbeddingModel()
    embeddings = model.encode_batch(["Hello world", "Tokyo travel guide"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_rag.py -v
```

Expected: FAIL — `rag.embeddings` does not exist

- [ ] **Step 3: Implement embeddings module**

`backend/src/smart_travel_buddy/rag/__init__.py`:
```python
```

`backend/src/smart_travel_buddy/rag/embeddings.py`:
```python
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingModel:
    def __init__(self):
        self._model = SentenceTransformer(MODEL_NAME)
        self.dimension = 384

    def encode(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts).tolist()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_rag.py -v
```

Expected: PASS (3 tests). First run will download the model (~80MB).

- [ ] **Step 5: Implement retriever**

`backend/src/smart_travel_buddy/rag/retriever.py`:
```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from smart_travel_buddy.rag.embeddings import EmbeddingModel

_embedding_model: EmbeddingModel | None = None


def get_embedding_model() -> EmbeddingModel:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


async def retrieve_chunks(session: AsyncSession, query: str, top_k: int = 5) -> list[dict]:
    model = get_embedding_model()
    query_embedding = model.encode(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    result = await session.execute(
        text("""
            SELECT id, source_file, chunk_text, metadata,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM knowledge_chunks
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """),
        {"embedding": embedding_str, "top_k": top_k},
    )

    chunks = []
    for row in result.mappings():
        chunks.append({
            "id": row["id"],
            "source_file": row["source_file"],
            "chunk_text": row["chunk_text"],
            "metadata": row["metadata"],
            "similarity": float(row["similarity"]),
        })
    return chunks
```

- [ ] **Step 6: Implement seed script**

`backend/src/smart_travel_buddy/rag/seed.py`:
```python
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from smart_travel_buddy.config import settings
from smart_travel_buddy.rag.embeddings import EmbeddingModel

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def chunk_text(text_content: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text_content.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def seed_knowledge(knowledge_dir: str):
    knowledge_path = Path(knowledge_dir)
    if not knowledge_path.exists():
        print(f"Knowledge directory not found: {knowledge_dir}")
        sys.exit(1)

    model = EmbeddingModel()
    engine = create_engine(settings.database_url_sync)

    md_files = list(knowledge_path.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files")

    with engine.connect() as conn:
        conn.execute(text("DELETE FROM knowledge_chunks"))
        conn.commit()

        total_chunks = 0
        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8")
            relative_path = str(md_file.relative_to(knowledge_path))
            category = md_file.parent.name
            chunks = chunk_text(content)

            for chunk in chunks:
                embedding = model.encode(chunk)
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                conn.execute(
                    text("""
                        INSERT INTO knowledge_chunks (source_file, chunk_text, embedding, metadata)
                        VALUES (:source_file, :chunk_text, :embedding::vector, :metadata::jsonb)
                    """),
                    {
                        "source_file": relative_path,
                        "chunk_text": chunk,
                        "embedding": embedding_str,
                        "metadata": f'{{"category": "{category}"}}',
                    },
                )
                total_chunks += 1

            print(f"  {relative_path}: {len(chunks)} chunks")

        conn.commit()
        print(f"Seeded {total_chunks} chunks from {len(md_files)} files")

    engine.dispose()


if __name__ == "__main__":
    knowledge_dir = sys.argv[1] if len(sys.argv) > 1 else "../../knowledge"
    seed_knowledge(knowledge_dir)
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/smart_travel_buddy/rag/ backend/tests/test_rag.py
git commit -m "feat: RAG engine with embeddings, retriever, and knowledge seeding"
```

---

### Task 7: Knowledge Base Content

**Files:**
- Create: `knowledge/destinations/*.md` (10 files)
- Create: `knowledge/cultural/*.md` (10 files)
- Create: `knowledge/packing/*.md` (4 files)

**Depends on:** Task 6 (RAG engine)

- [ ] **Step 1: Create destination guides**

Create 10 destination markdown files in `knowledge/destinations/`. Each file follows this structure (showing `tokyo.md` as the template — create all 10 following the same format):

`knowledge/destinations/tokyo.md`:
```markdown
# Tokyo, Japan

## Overview
Tokyo is Japan's capital and the world's most populous metropolitan area. A city where ultramodern skyscrapers stand alongside ancient temples, Tokyo offers an unmatched blend of tradition and innovation.

## Best Time to Visit
- **Spring (March-May):** Cherry blossom season, mild weather (15-22°C). Book well in advance.
- **Autumn (October-November):** Beautiful foliage, comfortable temperatures (15-22°C).
- **Summer (June-August):** Hot and humid (25-35°C), rainy season in June. Festival season.
- **Winter (December-February):** Cold but clear (2-10°C), fewer tourists, beautiful illuminations.

## Neighborhoods
- **Shinjuku:** Entertainment hub, nightlife, government district, great views from Tokyo Metropolitan Government Building (free).
- **Shibuya:** Youth culture, famous scramble crossing, shopping.
- **Asakusa:** Traditional area, Senso-ji Temple, Nakamise shopping street.
- **Akihabara:** Electronics, anime, manga culture.
- **Harajuku/Omotesando:** Fashion, Meiji Shrine, Takeshita Street.
- **Ginza:** Upscale shopping, galleries, kabuki theater.
- **Roppongi:** Art museums, nightlife, Tokyo Tower views.
- **Tsukiji/Toyosu:** Famous fish market, fresh sushi breakfast.

## Transportation
- **Suica/Pasmo card:** Rechargeable IC card for trains, buses, and convenience store purchases.
- **JR Yamanote Line:** Circular line connecting major stations. Essential for getting around.
- **Tokyo Metro:** 13 lines covering the entire city. Day passes available (~600 JPY).
- **From airports:** Narita Express (NEX) to central Tokyo (60 min), Limousine Bus, or Skyliner to Ueno.

## Must-See Spots
- Senso-ji Temple (Asakusa) — Tokyo's oldest temple
- Meiji Shrine (Harajuku) — Forested Shinto shrine
- teamLab Borderless — Immersive digital art museum
- Tsukiji Outer Market — Street food paradise
- Imperial Palace East Gardens — Free, beautiful gardens
- Tokyo Skytree — 634m observation tower
- Shinjuku Gyoen — Stunning garden combining Japanese, English, and French styles
- Akihabara — Electronics and otaku culture capital
```

Create the following files with similar depth and structure:
- `knowledge/destinations/paris.md` — Eiffel Tower, Louvre, Montmartre, arrondissements, Metro, bakeries
- `knowledge/destinations/new-york.md` — Manhattan, Brooklyn, subway, Central Park, Broadway, food scene
- `knowledge/destinations/rome.md` — Colosseum, Vatican, Trastevere, Italian cuisine, metro
- `knowledge/destinations/london.md` — Tube, British Museum, pubs, West End, neighborhoods
- `knowledge/destinations/barcelona.md` — Gaudi, La Rambla, Gothic Quarter, beaches, tapas
- `knowledge/destinations/bangkok.md` — Temples, street food, tuk-tuks, BTS/MRT, floating markets
- `knowledge/destinations/sydney.md` — Opera House, Bondi Beach, harbour, public transport
- `knowledge/destinations/cape-town.md` — Table Mountain, Cape Point, V&A Waterfront, wine regions
- `knowledge/destinations/rio-de-janeiro.md` — Christ the Redeemer, Copacabana, Sugarloaf, samba

- [ ] **Step 2: Create cultural guides**

Create 10 cultural markdown files in `knowledge/cultural/`. Each covers:
- Greetings and social norms
- Tipping customs
- Dining etiquette
- Dress codes
- Taboos and things to avoid
- Useful phrases

`knowledge/cultural/japan.md` (template):
```markdown
# Japan — Cultural Guide

## Greetings
- Bow when greeting. Deeper bows show more respect.
- Handshakes are acceptable for foreigners but bowing is appreciated.
- Use "-san" suffix when addressing people (e.g., Tanaka-san).

## Tipping
- Do NOT tip in Japan. It is considered rude or confusing.
- Service charges are included in restaurant bills.
- Exceptional service is acknowledged with a polite thank you.

## Dining Etiquette
- Say "itadakimasu" before eating and "gochisousama" after.
- Do not stick chopsticks upright in rice (funeral ritual).
- Slurping noodles is normal and shows appreciation.
- Pour drinks for others, not yourself.

## Dress Code
- Remove shoes when entering homes, temples, and some restaurants (look for shoe racks).
- Dress modestly at shrines and temples.
- Casual but neat is fine for most situations.

## Taboos
- Talking on phones on public transport is considered rude.
- Blowing your nose in public is frowned upon.
- Walking and eating simultaneously is uncommon.
- Avoid the number 4 (shi = death) in gifts.

## Useful Phrases
- Hello: Konnichiwa
- Thank you: Arigatou gozaimasu
- Excuse me: Sumimasen
- Where is...?: ...wa doko desu ka?
- How much?: Ikura desu ka?
```

Create similar files for: france.md, usa.md, italy.md, uk.md, spain.md, thailand.md, australia.md, south-africa.md, brazil.md.

- [ ] **Step 3: Create packing guides**

Create 4 packing guides in `knowledge/packing/`:

`knowledge/packing/tropical.md`:
```markdown
# Packing Guide — Tropical Climate

## Essentials
- Lightweight, breathable clothing (cotton, linen)
- Light rain jacket or compact umbrella
- Sunscreen SPF 50+
- Insect repellent (DEET or picaridin-based)
- Comfortable walking sandals
- Quick-dry towel
- Reusable water bottle

## Clothing
- Light t-shirts and shorts
- One light long-sleeve shirt (sun protection, temples)
- Swimwear
- Light cardigan for air-conditioned spaces
- Comfortable walking shoes (waterproof preferred)
- Hat or cap for sun protection

## Health
- Any prescribed medications
- Basic first aid kit
- Anti-diarrheal medication
- Oral rehydration salts
- Hand sanitizer

## Electronics
- Universal power adapter
- Portable phone charger
- Waterproof phone case
```

Create similar files for: winter.md, city-break.md, beach.md.

- [ ] **Step 4: Commit**

```bash
git add knowledge/
git commit -m "feat: knowledge base with destination guides, cultural tips, and packing checklists"
```

---

### Task 8: Backend API & WebSocket Server

**Files:**
- Create: `backend/src/smart_travel_buddy/server.py`
- Create: `backend/src/smart_travel_buddy/ws/__init__.py`
- Create: `backend/src/smart_travel_buddy/ws/handler.py`

**Depends on:** Task 2 (database)

- [ ] **Step 1: Create the FastAPI server**

`backend/src/smart_travel_buddy/server.py`:
```python
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from smart_travel_buddy.config import settings
from smart_travel_buddy.ws.handler import WebSocketHandler


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Smart Travel Buddy", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    handler = WebSocketHandler(websocket)
    try:
        await handler.run()
    except WebSocketDisconnect:
        await handler.cleanup()
```

- [ ] **Step 2: Create WebSocket handler**

`backend/src/smart_travel_buddy/ws/__init__.py`:
```python
```

`backend/src/smart_travel_buddy/ws/handler.py`:
```python
import asyncio
import json
import traceback

from fastapi import WebSocket

from smart_travel_buddy.config import settings


class WebSocketHandler:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.orchestrator = None
        self._task: asyncio.Task | None = None

    async def broadcast(self, event_type: str, data: dict):
        await self.ws.send_json({"type": event_type, **data})

    async def run(self):
        while True:
            raw = await self.ws.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await self.broadcast("error", {"message": "Invalid JSON"})
                continue

            action = message.get("action")
            if action == "start":
                await self._handle_start(message)
            elif action == "message":
                await self._handle_message(message)
            elif action == "cancel":
                await self._handle_cancel()
            else:
                await self.broadcast("error", {"message": f"Unknown action: {action}"})

    async def _handle_start(self, message: dict):
        from smart_travel_buddy.graph.orchestrator import create_orchestrator

        self.orchestrator = await create_orchestrator(self.broadcast)
        await self.broadcast("session_started", {"session_id": self.orchestrator.session_id})

    async def _handle_message(self, message: dict):
        if not self.orchestrator:
            await self.broadcast("error", {"message": "No active session. Send 'start' first."})
            return

        content = message.get("content", "")
        if self._task and not self._task.done():
            await self.broadcast("error", {"message": "Agent is busy processing. Please wait."})
            return

        self._task = asyncio.create_task(self._run_agent(content))

    async def _run_agent(self, user_message: str):
        try:
            await self.orchestrator.process_message(user_message)
        except Exception as e:
            traceback.print_exc()
            await self.broadcast("error", {"message": str(e)})

    async def _handle_cancel(self):
        if self._task and not self._task.done():
            self._task.cancel()
            await self.broadcast("cancelled", {})

    async def cleanup(self):
        if self._task and not self._task.done():
            self._task.cancel()
        if self.orchestrator:
            await self.orchestrator.close()
```

- [ ] **Step 3: Verify the server starts**

```bash
cd backend && source .venv/bin/activate
python -c "from smart_travel_buddy.server import app; print('Server module loads OK')"
```

Expected: `Server module loads OK`

- [ ] **Step 4: Commit**

```bash
git add backend/src/smart_travel_buddy/server.py backend/src/smart_travel_buddy/ws/
git commit -m "feat: FastAPI server with WebSocket handler"
```

---

### Task 9: LangGraph Interview Subgraph

**Files:**
- Create: `backend/src/smart_travel_buddy/graph/__init__.py`
- Create: `backend/src/smart_travel_buddy/graph/state.py`
- Create: `backend/src/smart_travel_buddy/graph/interview.py`
- Create: `backend/src/smart_travel_buddy/prompts/__init__.py`
- Create: `backend/src/smart_travel_buddy/prompts/interview.py`
- Create: `backend/tests/test_graph_interview.py`

**Depends on:** Task 8 (backend API)

- [ ] **Step 1: Write interview subgraph test**

`backend/tests/test_graph_interview.py`:
```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.graph.interview import should_continue_interview


def test_should_continue_interview_incomplete():
    state = TravelState(
        messages=[
            HumanMessage(content="I want to visit Tokyo"),
            AIMessage(content="Great! When are you planning to go?"),
        ],
        destination="",
        dates=None,
        interests=[],
        budget="",
        constraints=[],
        phase="interview",
        research_results={},
        itinerary=None,
    )
    result = should_continue_interview(state)
    assert result == "continue"


def test_should_continue_interview_complete():
    state = TravelState(
        messages=[
            HumanMessage(content="I want to visit Tokyo"),
            AIMessage(content="When are you planning to go?"),
            HumanMessage(content="July 10-14"),
            AIMessage(content="What are your interests?"),
            HumanMessage(content="Food and culture"),
            AIMessage(content='{"ready": true}'),
        ],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["food", "culture"],
        budget="mid-range",
        constraints=[],
        phase="interview",
        research_results={},
        itinerary=None,
    )
    result = should_continue_interview(state)
    assert result == "complete"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_graph_interview.py -v
```

Expected: FAIL — modules do not exist

- [ ] **Step 3: Create state definitions**

`backend/src/smart_travel_buddy/graph/__init__.py`:
```python
```

`backend/src/smart_travel_buddy/graph/state.py`:
```python
from typing import Any

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class TravelState(TypedDict):
    messages: list[BaseMessage]
    destination: str
    dates: dict | None
    interests: list[str]
    budget: str
    constraints: list[str]
    phase: str
    research_results: dict[str, Any]
    itinerary: dict | None
```

- [ ] **Step 4: Create interview prompt**

`backend/src/smart_travel_buddy/prompts/__init__.py`:
```python
```

`backend/src/smart_travel_buddy/prompts/interview.py`:
```python
INTERVIEW_SYSTEM_PROMPT = """You are a friendly and knowledgeable travel planning assistant called Smart Travel Buddy.

Your job is to gather travel requirements through natural conversation. Ask ONE question at a time.

You need to collect:
1. **Destination** — Where they want to go
2. **Dates** — When they want to travel (start and end dates)
3. **Interests** — What they enjoy (culture, food, adventure, relaxation, nightlife, nature, shopping)
4. **Budget** — Budget level (budget, mid-range, luxury)
5. **Constraints** — Any special needs (dietary restrictions, accessibility, traveling with kids, etc.)

Guidelines:
- Be warm and enthusiastic about their chosen destination.
- Ask only ONE question per message.
- If they mention a destination, acknowledge it with a fun fact.
- Don't force every question — if they volunteer info, accept it.
- Once you have enough information (at minimum: destination, dates, and interests), include the following JSON block at the END of your response:

```json
{"ready": true, "destination": "City, Country", "dates": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}, "interests": ["interest1", "interest2"], "budget": "mid-range", "constraints": []}
```

If information is missing, do NOT include the JSON block — ask for it instead."""
```

- [ ] **Step 5: Create interview subgraph**

`backend/src/smart_travel_buddy/graph/interview.py`:
```python
import json
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.prompts.interview import INTERVIEW_SYSTEM_PROMPT


def should_continue_interview(state: TravelState) -> str:
    if state["destination"] and state["dates"] and state["interests"]:
        return "complete"

    last_message = state["messages"][-1] if state["messages"] else None
    if isinstance(last_message, AIMessage):
        try:
            json_match = re.search(r'\{[^{}]*"ready"\s*:\s*true[^{}]*\}', last_message.content)
            if json_match:
                return "complete"
        except (json.JSONDecodeError, AttributeError):
            pass

    return "continue"


def extract_travel_info(state: TravelState) -> TravelState:
    last_message = state["messages"][-1] if state["messages"] else None
    if not isinstance(last_message, AIMessage):
        return state

    try:
        json_match = re.search(r'\{[^{}]*"ready"\s*:\s*true[^{}]*\}', last_message.content)
        if json_match:
            data = json.loads(json_match.group())
            return {
                **state,
                "destination": data.get("destination", state["destination"]),
                "dates": data.get("dates", state["dates"]),
                "interests": data.get("interests", state["interests"]),
                "budget": data.get("budget", state["budget"]),
                "constraints": data.get("constraints", state["constraints"]),
                "phase": "research",
            }
    except (json.JSONDecodeError, AttributeError):
        pass

    return state


async def interview_node(state: TravelState, config) -> TravelState:
    llm = config["configurable"]["llm"]

    messages_with_system = [SystemMessage(content=INTERVIEW_SYSTEM_PROMPT)] + state["messages"]

    response = await llm.ainvoke(messages_with_system)

    new_messages = list(state["messages"]) + [response]
    new_state = {**state, "messages": new_messages}

    return extract_travel_info(new_state)


def build_interview_graph() -> StateGraph:
    graph = StateGraph(TravelState)
    graph.add_node("interview", interview_node)
    graph.set_entry_point("interview")

    graph.add_conditional_edges(
        "interview",
        should_continue_interview,
        {"continue": "__end__", "complete": "__end__"},
    )

    return graph
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_graph_interview.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add backend/src/smart_travel_buddy/graph/ backend/src/smart_travel_buddy/prompts/ \
       backend/tests/test_graph_interview.py
git commit -m "feat: LangGraph interview subgraph with human-in-the-loop"
```

---

### Task 10: LangGraph Research Subgraph

**Files:**
- Create: `backend/src/smart_travel_buddy/graph/research.py`
- Create: `backend/tests/test_graph_research.py`

**Depends on:** Tasks 3-5 (MCPs), Task 6 (RAG), Task 9 (interview subgraph)

- [ ] **Step 1: Write research subgraph test**

`backend/tests/test_graph_research.py`:
```python
import json
from unittest.mock import AsyncMock, patch

import pytest

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.graph.research import call_weather, call_currency, call_wikipedia


@pytest.mark.asyncio
async def test_call_weather():
    mock_tool = AsyncMock()
    mock_tool.ainvoke.return_value = json.dumps({
        "city": "Tokyo",
        "country": "JP",
        "forecast": [{"date": "2026-07-10", "temp_min": 24, "temp_max": 31, "condition": "partly cloudy", "icon": "02d"}],
    })

    state = TravelState(
        messages=[],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["food", "culture"],
        budget="mid-range",
        constraints=[],
        phase="research",
        research_results={},
        itinerary=None,
    )

    result = await call_weather(state, {"configurable": {"mcp_tools": {"weather": [mock_tool]}, "broadcast": AsyncMock()}})
    assert "weather" in result["research_results"]


@pytest.mark.asyncio
async def test_call_currency():
    mock_tool = AsyncMock()
    mock_tool.ainvoke.return_value = json.dumps({
        "from": "USD",
        "to": "JPY",
        "rate": 149.5,
        "date": "2026-05-21",
    })

    state = TravelState(
        messages=[],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["food"],
        budget="mid-range",
        constraints=[],
        phase="research",
        research_results={},
        itinerary=None,
    )

    result = await call_currency(state, {"configurable": {"mcp_tools": {"currency": [mock_tool]}, "broadcast": AsyncMock()}})
    assert "currency" in result["research_results"]


@pytest.mark.asyncio
async def test_call_wikipedia():
    mock_tool = AsyncMock()
    mock_tool.ainvoke.return_value = json.dumps({
        "title": "Tokyo",
        "extract": "Tokyo is the capital of Japan.",
        "description": "Capital city of Japan",
        "thumbnail": "",
    })

    state = TravelState(
        messages=[],
        destination="Tokyo, Japan",
        dates={"start": "2026-07-10", "end": "2026-07-14"},
        interests=["culture"],
        budget="mid-range",
        constraints=[],
        phase="research",
        research_results={},
        itinerary=None,
    )

    result = await call_wikipedia(state, {"configurable": {"mcp_tools": {"wikipedia": [mock_tool]}, "broadcast": AsyncMock()}})
    assert "wikipedia" in result["research_results"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_graph_research.py -v
```

Expected: FAIL — `research` module does not exist

- [ ] **Step 3: Implement research subgraph**

`backend/src/smart_travel_buddy/graph/research.py`:
```python
import asyncio
import json
from typing import Any

from langgraph.graph import StateGraph

from smart_travel_buddy.graph.state import TravelState


DESTINATION_CURRENCIES = {
    "japan": "JPY", "france": "EUR", "usa": "USD", "italy": "EUR",
    "uk": "GBP", "spain": "EUR", "thailand": "THB", "australia": "AUD",
    "south africa": "ZAR", "brazil": "BRL", "germany": "EUR",
    "mexico": "MXN", "india": "INR", "canada": "CAD",
}


def _guess_currency(destination: str) -> str:
    dest_lower = destination.lower()
    for country, currency in DESTINATION_CURRENCIES.items():
        if country in dest_lower:
            return currency
    return "EUR"


def _extract_city(destination: str) -> tuple[str, str]:
    parts = [p.strip() for p in destination.split(",")]
    city = parts[0]
    country_code = parts[1][:2].upper() if len(parts) > 1 else ""
    return city, country_code


async def call_weather(state: TravelState, config) -> dict:
    broadcast = config["configurable"]["broadcast"]
    await broadcast("progress", {"step": "weather", "status": "started", "label": f"Checking weather for {state['destination']}..."})

    tools = config["configurable"]["mcp_tools"].get("weather", [])
    city, country_code = _extract_city(state["destination"])
    days = 5
    if state["dates"]:
        from datetime import datetime
        start = datetime.strptime(state["dates"]["start"], "%Y-%m-%d")
        end = datetime.strptime(state["dates"]["end"], "%Y-%m-%d")
        days = min((end - start).days + 1, 5)

    result = {}
    for tool in tools:
        if "forecast" in tool.name:
            raw = await tool.ainvoke({"city": city, "country_code": country_code, "days": days})
            result = json.loads(raw) if isinstance(raw, str) else raw
            break

    await broadcast("progress", {"step": "weather", "status": "complete"})

    new_results = {**state["research_results"], "weather": result}
    return {"research_results": new_results}


async def call_currency(state: TravelState, config) -> dict:
    broadcast = config["configurable"]["broadcast"]
    dest_currency = _guess_currency(state["destination"])
    await broadcast("progress", {"step": "currency", "status": "started", "label": f"Converting USD to {dest_currency}..."})

    tools = config["configurable"]["mcp_tools"].get("currency", [])

    result = {}
    for tool in tools:
        if "exchange_rate" in tool.name:
            raw = await tool.ainvoke({"from_currency": "USD", "to_currency": dest_currency})
            result = json.loads(raw) if isinstance(raw, str) else raw
            break

    await broadcast("progress", {"step": "currency", "status": "complete"})

    new_results = {**state["research_results"], "currency": result}
    return {"research_results": new_results}


async def call_wikipedia(state: TravelState, config) -> dict:
    broadcast = config["configurable"]["broadcast"]
    city, _ = _extract_city(state["destination"])
    await broadcast("progress", {"step": "wikipedia", "status": "started", "label": f"Researching {city}..."})

    tools = config["configurable"]["mcp_tools"].get("wikipedia", [])

    result = {}
    for tool in tools:
        if "summary" in tool.name:
            raw = await tool.ainvoke({"topic": city})
            result = json.loads(raw) if isinstance(raw, str) else raw
            break

    await broadcast("progress", {"step": "wikipedia", "status": "complete"})

    new_results = {**state["research_results"], "wikipedia": result}
    return {"research_results": new_results}


async def call_rag(state: TravelState, config) -> dict:
    broadcast = config["configurable"]["broadcast"]
    await broadcast("progress", {"step": "rag", "status": "started", "label": "Searching travel knowledge..."})

    db_session = config["configurable"].get("db_session")
    if db_session:
        from smart_travel_buddy.rag.retriever import retrieve_chunks

        query = f"{state['destination']} {' '.join(state['interests'])}"
        chunks = await retrieve_chunks(db_session, query, top_k=8)
        rag_context = "\n\n".join(c["chunk_text"] for c in chunks)
    else:
        rag_context = ""

    await broadcast("progress", {"step": "rag", "status": "complete"})

    new_results = {**state["research_results"], "rag_context": rag_context}
    return {"research_results": new_results}


def build_research_graph() -> StateGraph:
    graph = StateGraph(TravelState)

    graph.add_node("weather", call_weather)
    graph.add_node("currency", call_currency)
    graph.add_node("wikipedia", call_wikipedia)
    graph.add_node("rag", call_rag)

    graph.set_entry_point("weather")
    graph.add_edge("weather", "currency")
    graph.add_edge("currency", "wikipedia")
    graph.add_edge("wikipedia", "rag")
    graph.add_edge("rag", "__end__")

    return graph
```

Note: The nodes run sequentially in this graph definition. For true parallel fan-out, the orchestrator will use `asyncio.gather` to run weather, currency, and wikipedia concurrently before RAG. This simpler sequential structure works for testing and can be upgraded to parallel in the orchestrator.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_graph_research.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/smart_travel_buddy/graph/research.py backend/tests/test_graph_research.py
git commit -m "feat: LangGraph research subgraph with MCP fan-out and RAG"
```

---

### Task 11: LangGraph Itinerary Subgraph & Orchestrator

**Files:**
- Create: `backend/src/smart_travel_buddy/graph/itinerary.py`
- Create: `backend/src/smart_travel_buddy/prompts/itinerary.py`
- Create: `backend/src/smart_travel_buddy/graph/orchestrator.py`
- Create: `backend/tests/test_graph_itinerary.py`

**Depends on:** Task 10 (research subgraph)

- [ ] **Step 1: Write itinerary subgraph test**

`backend/tests/test_graph_itinerary.py`:
```python
import json
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.graph.itinerary import parse_itinerary_json


def test_parse_itinerary_json_from_response():
    itinerary_data = {
        "destination": "Tokyo, Japan",
        "dates": {"start": "2026-07-10", "end": "2026-07-14"},
        "currency": {"from": "USD", "to": "JPY", "rate": 149.5},
        "packing": ["light rain jacket"],
        "cultural_tips": ["Bow when greeting"],
        "days": [
            {
                "date": "2026-07-10",
                "weather": {"temp_high": 31, "temp_low": 24, "condition": "Partly cloudy", "icon": "02d"},
                "activities": [{"name": "Senso-ji Temple", "time": "morning", "description": "Historic temple", "tip": "Go early"}],
            }
        ],
    }

    response_text = f"Here is your itinerary:\n```json\n{json.dumps(itinerary_data)}\n```"

    result = parse_itinerary_json(response_text)
    assert result is not None
    assert result["destination"] == "Tokyo, Japan"
    assert len(result["days"]) == 1
    assert result["days"][0]["activities"][0]["name"] == "Senso-ji Temple"


def test_parse_itinerary_json_no_json():
    result = parse_itinerary_json("Here is a plain text response with no JSON.")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_graph_itinerary.py -v
```

Expected: FAIL — `itinerary` module does not exist

- [ ] **Step 3: Create itinerary prompt**

`backend/src/smart_travel_buddy/prompts/itinerary.py`:
```python
ITINERARY_SYSTEM_PROMPT = """You are a travel itinerary generator. Given research data about a destination (weather, currency, cultural info, travel guides), create a detailed day-by-day itinerary.

You MUST respond with a JSON block wrapped in ```json ... ``` markers. The JSON must follow this exact schema:

```json
{{
  "destination": "City, Country",
  "dates": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}},
  "currency": {{"from": "USD", "to": "LOCAL", "rate": 0.0}},
  "packing": ["item1", "item2"],
  "cultural_tips": ["tip1", "tip2"],
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "weather": {{
        "temp_high": 0,
        "temp_low": 0,
        "condition": "description",
        "icon": "icon_code"
      }},
      "activities": [
        {{
          "name": "Activity Name",
          "time": "morning|afternoon|evening",
          "description": "Brief description",
          "tip": "Practical tip for this activity"
        }}
      ]
    }}
  ]
}}
```

Guidelines:
- Plan 3-4 activities per day (morning, afternoon, evening).
- Match activities to the user's interests.
- Adapt suggestions to weather (indoor activities on rainy days).
- Include a mix of popular spots and local gems.
- Keep descriptions concise (1-2 sentences max).
- Include practical tips (best time to visit, what to bring, how to get there).
- Suggest 5-8 packing items relevant to the weather and activities.
- Include 3-5 cultural tips specific to the destination.
- Use weather data to set realistic temp_high/temp_low values.
- If weather data is unavailable, use seasonal averages.
"""
```

- [ ] **Step 4: Implement itinerary subgraph**

`backend/src/smart_travel_buddy/graph/itinerary.py`:
```python
import json
import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph

from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.prompts.itinerary import ITINERARY_SYSTEM_PROMPT


def parse_itinerary_json(text: str) -> dict | None:
    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def _build_research_context(state: TravelState) -> str:
    parts = []
    results = state["research_results"]

    if "weather" in results:
        parts.append(f"## Weather Forecast\n{json.dumps(results['weather'], indent=2)}")

    if "currency" in results:
        parts.append(f"## Currency\n{json.dumps(results['currency'], indent=2)}")

    if "wikipedia" in results:
        wiki = results["wikipedia"]
        parts.append(f"## Destination Info\n{wiki.get('extract', '')}")

    if "rag_context" in results:
        parts.append(f"## Travel Knowledge\n{results['rag_context']}")

    return "\n\n".join(parts)


async def itinerary_node(state: TravelState, config) -> TravelState:
    llm = config["configurable"]["llm"]
    broadcast = config["configurable"]["broadcast"]

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

    response = await llm.ainvoke(messages)

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


def build_itinerary_graph() -> StateGraph:
    graph = StateGraph(TravelState)
    graph.add_node("generate", itinerary_node)
    graph.set_entry_point("generate")
    graph.add_edge("generate", "__end__")
    return graph
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && source .venv/bin/activate
pytest tests/test_graph_itinerary.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 6: Implement orchestrator**

`backend/src/smart_travel_buddy/graph/orchestrator.py`:
```python
import uuid
from typing import Any, Callable, Coroutine

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from smart_travel_buddy.config import settings
from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.graph.interview import build_interview_graph, should_continue_interview
from smart_travel_buddy.graph.research import (
    call_weather,
    call_currency,
    call_wikipedia,
    call_rag,
)
from smart_travel_buddy.graph.itinerary import build_itinerary_graph, itinerary_node


BroadcastFn = Callable[[str, dict], Coroutine[Any, Any, None]]


class Orchestrator:
    def __init__(self, broadcast: BroadcastFn):
        self.session_id = str(uuid.uuid4())
        self.broadcast = broadcast
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        self.memory = MemorySaver()
        self.interview_graph = build_interview_graph().compile(checkpointer=self.memory)
        self.itinerary_graph = build_itinerary_graph().compile()
        self.state: TravelState = {
            "messages": [],
            "destination": "",
            "dates": None,
            "interests": [],
            "budget": "",
            "constraints": [],
            "phase": "interview",
            "research_results": {},
            "itinerary": None,
        }
        self.mcp_client = None

    async def _init_mcp_client(self):
        from langchain_mcp_adapters.client import MultiServerMCPClient

        self.mcp_client = MultiServerMCPClient(
            {
                "weather": {"url": settings.mcp_weather_url, "transport": "sse"},
                "currency": {"url": settings.mcp_currency_url, "transport": "sse"},
                "wikipedia": {"url": settings.mcp_wikipedia_url, "transport": "sse"},
            }
        )
        await self.mcp_client.__aenter__()

    def _get_mcp_tools(self) -> dict[str, list]:
        if not self.mcp_client:
            return {}
        all_tools = self.mcp_client.get_tools()
        categorized = {"weather": [], "currency": [], "wikipedia": []}
        for tool in all_tools:
            name = tool.name.lower()
            if "forecast" in name or "weather" in name:
                categorized["weather"].append(tool)
            elif "exchange" in name or "convert" in name or "currency" in name:
                categorized["currency"].append(tool)
            elif "summary" in name or "search" in name or "wikipedia" in name:
                categorized["wikipedia"].append(tool)
        return categorized

    async def process_message(self, user_message: str):
        self.state["messages"] = list(self.state["messages"]) + [HumanMessage(content=user_message)]

        if self.state["phase"] == "interview":
            await self._run_interview()
        elif self.state["phase"] == "research":
            await self._run_research()
            await self._run_itinerary()
        elif self.state["phase"] == "refinement":
            await self._run_refinement(user_message)

    async def _run_interview(self):
        config = {
            "configurable": {
                "llm": self.llm,
                "broadcast": self.broadcast,
                "thread_id": self.session_id,
            }
        }

        result = await self.interview_graph.ainvoke(self.state, config)
        self.state = {**self.state, **result}

        last_msg = self.state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        await self.broadcast("agent_message", {"content": content})

        if self.state["phase"] == "research":
            await self._run_research()
            await self._run_itinerary()

    async def _run_research(self):
        await self.broadcast("phase_change", {"phase": "research"})

        if not self.mcp_client:
            await self._init_mcp_client()

        config = {
            "configurable": {
                "mcp_tools": self._get_mcp_tools(),
                "broadcast": self.broadcast,
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

    async def _run_itinerary(self):
        config = {
            "configurable": {
                "llm": self.llm,
                "broadcast": self.broadcast,
            }
        }

        result = await self.itinerary_graph.ainvoke(self.state, config)
        self.state = {**self.state, **result}

    async def _run_refinement(self, user_message: str):
        config = {
            "configurable": {
                "llm": self.llm,
                "broadcast": self.broadcast,
            }
        }

        result = await itinerary_node(self.state, config)
        self.state = {**self.state, **result}

    async def close(self):
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)


async def create_orchestrator(broadcast: BroadcastFn) -> Orchestrator:
    return Orchestrator(broadcast)
```

- [ ] **Step 7: Commit**

```bash
git add backend/src/smart_travel_buddy/graph/itinerary.py \
       backend/src/smart_travel_buddy/graph/orchestrator.py \
       backend/src/smart_travel_buddy/prompts/itinerary.py \
       backend/tests/test_graph_itinerary.py
git commit -m "feat: LangGraph itinerary subgraph and orchestrator"
```

---

### Task 12: Frontend Scaffolding & Chat Panel

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/App.css`
- Create: `frontend/src/lib/utils.js`
- Create: `frontend/src/hooks/useWebSocket.js`
- Create: `frontend/src/components/ChatPanel.jsx`
- Create: `frontend/src/components/MessageBubble.jsx`
- Create: `frontend/src/components/ThinkingBubble.jsx`

**Independent:** Can start in parallel with backend tasks.

- [ ] **Step 1: Initialize frontend project**

`frontend/package.json`:
```json
{
  "name": "smart-travel-buddy-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.460.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^6.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "autoprefixer": "^10.4.0"
  }
}
```

`frontend/vite.config.js`:
```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      "/ws": {
        target: "http://localhost:8000",
        ws: true,
      },
      "/health": {
        target: "http://localhost:8000",
      },
    },
  },
});
```

`frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Smart Travel Buddy</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

`frontend/src/main.jsx`:
```jsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./App.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

`frontend/src/lib/utils.js`:
```javascript
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Create global styles**

`frontend/src/App.css`:
```css
@import "tailwindcss";

:root {
  --color-primary: #1e40af;
  --color-primary-light: #3b82f6;
  --color-accent: #f59e0b;
  --color-accent-light: #fbbf24;
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-text: #1e293b;
  --color-text-muted: #64748b;
  --color-thinking: #f1f5f9;
  --color-border: #e2e8f0;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: var(--color-bg);
  color: var(--color-text);
}

* {
  box-sizing: border-box;
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-pulse-dot {
  animation: pulseDot 1.5s ease-in-out infinite;
}

@keyframes pulseDot {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
```

- [ ] **Step 3: Create WebSocket hook**

`frontend/src/hooks/useWebSocket.js`:
```javascript
import { useEffect, useRef, useState, useCallback } from "react";

export function useWebSocket(url) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ action: "start" }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimeoutRef.current = setTimeout(connect, 2000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { connected, lastMessage, send };
}
```

- [ ] **Step 4: Create ThinkingBubble component**

`frontend/src/components/ThinkingBubble.jsx`:
```jsx
import { useState } from "react";
import { ChevronDown, ChevronRight, Brain } from "lucide-react";

export default function ThinkingBubble({ content }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="animate-fade-in flex justify-start mb-2">
      <div
        className="max-w-[80%] rounded-lg px-3 py-2 text-sm cursor-pointer select-none"
        style={{ backgroundColor: "var(--color-thinking)", color: "var(--color-text-muted)" }}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-1.5 font-medium">
          <Brain size={14} />
          <span>Thinking</span>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
        {expanded && (
          <div className="mt-2 italic whitespace-pre-wrap text-xs leading-relaxed">
            {content}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create MessageBubble component**

`frontend/src/components/MessageBubble.jsx`:
```jsx
import ThinkingBubble from "./ThinkingBubble";

function parseThinking(content) {
  const thinkRegex = /<think(?:ing)?>([\s\S]*?)<\/think(?:ing)?>/gi;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = thinkRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: content.slice(lastIndex, match.index) });
    }
    parts.push({ type: "thinking", content: match[1].trim() });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: "text", content: content.slice(lastIndex) });
  }

  return parts.length > 0 ? parts : [{ type: "text", content }];
}

export default function MessageBubble({ role, content }) {
  const isUser = role === "user";
  const parts = isUser ? [{ type: "text", content }] : parseThinking(content);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className="flex flex-col gap-1 max-w-[80%]">
        {parts.map((part, i) =>
          part.type === "thinking" ? (
            <ThinkingBubble key={i} content={part.content} />
          ) : part.content.trim() ? (
            <div
              key={i}
              className={`animate-fade-in rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                isUser
                  ? "bg-[var(--color-primary)] text-white rounded-br-md"
                  : "bg-[var(--color-surface)] border border-[var(--color-border)] rounded-bl-md"
              }`}
            >
              <div className="whitespace-pre-wrap">{part.content}</div>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create ChatPanel component**

`frontend/src/components/ChatPanel.jsx`:
```jsx
import { useState, useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import MessageBubble from "./MessageBubble";

export default function ChatPanel({ messages, onSend, isProcessing, connected }) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold" style={{ color: "var(--color-primary)" }}>
          Smart Travel Buddy
        </h2>
        <div className="flex items-center gap-1.5 text-xs">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-400"}`} />
          <span style={{ color: "var(--color-text-muted)" }}>{connected ? "Connected" : "Disconnected"}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="text-center mt-12" style={{ color: "var(--color-text-muted)" }}>
            <p className="text-lg mb-1">Where would you like to go?</p>
            <p className="text-sm">Tell me your dream destination and I'll plan the perfect trip.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
        {isProcessing && (
          <div className="flex justify-start mb-3">
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl rounded-bl-md px-4 py-2.5">
              <div className="flex gap-1">
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)]" style={{ animationDelay: "0ms" }} />
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)]" style={{ animationDelay: "300ms" }} />
                <span className="animate-pulse-dot w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)]" style={{ animationDelay: "600ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-[var(--color-border)]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell me about your trip..."
            disabled={!connected || isProcessing}
            className="flex-1 px-4 py-2.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-light)] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!connected || isProcessing || !input.trim()}
            className="px-4 py-2.5 rounded-xl text-white text-sm font-medium bg-[var(--color-primary)] hover:bg-[var(--color-primary-light)] disabled:opacity-50 transition-colors"
          >
            {isProcessing ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 7: Create App.jsx**

`frontend/src/App.jsx`:
```jsx
import { useState, useEffect, useCallback } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import ChatPanel from "./components/ChatPanel";

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws`;

export default function App() {
  const [messages, setMessages] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [itinerary, setItinerary] = useState(null);
  const [progress, setProgress] = useState([]);
  const [phase, setPhase] = useState("interview");

  const { connected, lastMessage, send } = useWebSocket(WS_URL);

  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case "agent_message":
        setMessages((prev) => [...prev, { role: "assistant", content: lastMessage.content }]);
        setIsProcessing(false);
        break;
      case "phase_change":
        setPhase(lastMessage.phase);
        break;
      case "progress":
        setProgress((prev) => {
          const existing = prev.findIndex((p) => p.step === lastMessage.step);
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = lastMessage;
            return updated;
          }
          return [...prev, lastMessage];
        });
        break;
      case "itinerary":
        setItinerary(lastMessage.data);
        setProgress([]);
        setIsProcessing(false);
        break;
      case "error":
        setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${lastMessage.message}` }]);
        setIsProcessing(false);
        break;
    }
  }, [lastMessage]);

  const handleSend = useCallback(
    (content) => {
      setMessages((prev) => [...prev, { role: "user", content }]);
      setIsProcessing(true);
      send({ action: "message", content });
    },
    [send]
  );

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
          <div className="max-w-2xl mx-auto space-y-3">
            <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--color-primary)" }}>
              Researching your trip...
            </h2>
            {progress.map((p, i) => (
              <div
                key={i}
                className="animate-fade-in flex items-center gap-3 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-4 py-3"
              >
                <div
                  className={`w-2.5 h-2.5 rounded-full ${
                    p.status === "complete" ? "bg-green-500" : "bg-[var(--color-accent)] animate-pulse"
                  }`}
                />
                <span className="text-sm">{p.label || p.step}</span>
                {p.status === "complete" && <span className="ml-auto text-green-600 text-xs font-medium">Done</span>}
              </div>
            ))}
          </div>
        )}

        {itinerary && (
          <div className="max-w-2xl mx-auto">
            <p className="text-center text-sm" style={{ color: "var(--color-text-muted)" }}>
              Itinerary view coming soon — data loaded for {itinerary.destination}
            </p>
          </div>
        )}

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
    </div>
  );
}
```

- [ ] **Step 8: Install dependencies and verify build**

```bash
cd frontend
npm install
npm run build
```

Expected: Build succeeds, `dist/` directory created.

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffolding with chat panel, thinking bubbles, and WebSocket"
```

---

### Task 13: Frontend Itinerary & Progress Views

**Files:**
- Create: `frontend/src/components/ItineraryView.jsx`
- Create: `frontend/src/components/DayCard.jsx`
- Create: `frontend/src/components/WeatherBadge.jsx`
- Create: `frontend/src/components/ProgressCards.jsx`
- Create: `frontend/src/components/PackingChecklist.jsx`
- Create: `frontend/src/components/CulturalTips.jsx`
- Create: `frontend/src/components/CurrencyConverter.jsx`
- Modify: `frontend/src/App.jsx` — replace placeholder with real components

**Depends on:** Task 12 (frontend scaffolding)

- [ ] **Step 1: Create WeatherBadge**

`frontend/src/components/WeatherBadge.jsx`:
```jsx
export default function WeatherBadge({ weather }) {
  if (!weather) return null;

  const iconUrl = weather.icon
    ? `https://openweathermap.org/img/wn/${weather.icon}@2x.png`
    : null;

  return (
    <div className="flex items-center gap-2 bg-blue-50 rounded-lg px-3 py-1.5">
      {iconUrl && <img src={iconUrl} alt={weather.condition} className="w-8 h-8" />}
      <div className="text-xs">
        <div className="font-semibold text-blue-800">
          {weather.temp_high}° / {weather.temp_low}°
        </div>
        <div className="text-blue-600 capitalize">{weather.condition}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create DayCard**

`frontend/src/components/DayCard.jsx`:
```jsx
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import WeatherBadge from "./WeatherBadge";

const TIME_COLORS = {
  morning: "bg-amber-100 text-amber-800",
  afternoon: "bg-sky-100 text-sky-800",
  evening: "bg-indigo-100 text-indigo-800",
};

export default function DayCard({ day, dayNumber }) {
  const [expanded, setExpanded] = useState(true);

  const date = new Date(day.date + "T00:00:00");
  const formattedDate = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="animate-fade-in bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl overflow-hidden">
      {/* Day header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="text-xs font-bold text-white bg-[var(--color-primary)] rounded-full w-7 h-7 flex items-center justify-center">
            {dayNumber}
          </div>
          <div>
            <div className="font-semibold text-sm">{formattedDate}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <WeatherBadge weather={day.weather} />
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </div>

      {/* Activities */}
      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {day.activities?.map((activity, i) => (
            <div key={i} className="flex gap-3 py-2 border-t border-[var(--color-border)] first:border-t-0">
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full h-fit mt-0.5 ${TIME_COLORS[activity.time] || TIME_COLORS.morning}`}>
                {activity.time}
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{activity.name}</div>
                <div className="text-xs mt-0.5" style={{ color: "var(--color-text-muted)" }}>
                  {activity.description}
                </div>
                {activity.tip && (
                  <div className="text-xs mt-1 italic text-amber-700">
                    Tip: {activity.tip}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create PackingChecklist**

`frontend/src/components/PackingChecklist.jsx`:
```jsx
import { useState } from "react";
import { Luggage } from "lucide-react";

export default function PackingChecklist({ items }) {
  const [checked, setChecked] = useState({});

  if (!items || items.length === 0) return null;

  const toggle = (i) => setChecked((prev) => ({ ...prev, [i]: !prev[i] }));

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Luggage size={16} style={{ color: "var(--color-primary)" }} />
        <h3 className="font-semibold text-sm">Packing List</h3>
      </div>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <label key={i} className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={!!checked[i]}
              onChange={() => toggle(i)}
              className="rounded border-gray-300 text-[var(--color-primary)] focus:ring-[var(--color-primary-light)]"
            />
            <span className={checked[i] ? "line-through text-gray-400" : ""}>{item}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create CulturalTips**

`frontend/src/components/CulturalTips.jsx`:
```jsx
import { useState } from "react";
import { Globe, ChevronDown, ChevronRight } from "lucide-react";

export default function CulturalTips({ tips }) {
  const [expanded, setExpanded] = useState(false);

  if (!tips || tips.length === 0) return null;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Globe size={16} style={{ color: "var(--color-primary)" }} />
          <h3 className="font-semibold text-sm">Cultural Tips</h3>
        </div>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </div>
      {expanded && (
        <ul className="mt-3 space-y-1.5">
          {tips.map((tip, i) => (
            <li key={i} className="text-sm flex gap-2">
              <span className="text-amber-500 mt-0.5">&#8226;</span>
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Create CurrencyConverter**

`frontend/src/components/CurrencyConverter.jsx`:
```jsx
import { useState } from "react";
import { ArrowLeftRight } from "lucide-react";

export default function CurrencyConverter({ currency }) {
  const [amount, setAmount] = useState("100");

  if (!currency) return null;

  const converted = (parseFloat(amount || "0") * currency.rate).toFixed(2);

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <ArrowLeftRight size={16} style={{ color: "var(--color-primary)" }} />
        <h3 className="font-semibold text-sm">Currency</h3>
        <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>
          1 {currency.from} = {currency.rate} {currency.to}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500">{currency.from}</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full px-3 py-1.5 rounded-lg border border-[var(--color-border)] text-sm focus:outline-none focus:ring-1 focus:ring-[var(--color-primary-light)]"
          />
        </div>
        <ArrowLeftRight size={14} className="mt-4 text-gray-400" />
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500">{currency.to}</label>
          <div className="px-3 py-1.5 rounded-lg bg-gray-50 border border-[var(--color-border)] text-sm font-medium">
            {converted}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create ItineraryView**

`frontend/src/components/ItineraryView.jsx`:
```jsx
import DayCard from "./DayCard";
import PackingChecklist from "./PackingChecklist";
import CulturalTips from "./CulturalTips";
import CurrencyConverter from "./CurrencyConverter";
import { MapPin, Calendar } from "lucide-react";

export default function ItineraryView({ itinerary }) {
  if (!itinerary) return null;

  const startDate = itinerary.dates?.start
    ? new Date(itinerary.dates.start + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : "";
  const endDate = itinerary.dates?.end
    ? new Date(itinerary.dates.end + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "";

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in bg-gradient-to-r from-blue-600 to-blue-800 text-white rounded-2xl p-6 mb-6">
        <h1 className="text-2xl font-bold mb-2">{itinerary.destination}</h1>
        <div className="flex items-center gap-4 text-blue-100 text-sm">
          <div className="flex items-center gap-1.5">
            <Calendar size={14} />
            <span>{startDate} — {endDate}</span>
          </div>
          {itinerary.currency && (
            <div className="flex items-center gap-1.5">
              <span>1 {itinerary.currency.from} = {itinerary.currency.rate} {itinerary.currency.to}</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-6">
        {/* Day cards */}
        <div className="flex-1 space-y-4">
          {itinerary.days?.map((day, i) => (
            <DayCard key={i} day={day} dayNumber={i + 1} />
          ))}
        </div>

        {/* Sidebar widgets */}
        <div className="w-64 space-y-4 shrink-0">
          <CurrencyConverter currency={itinerary.currency} />
          <PackingChecklist items={itinerary.packing} />
          <CulturalTips tips={itinerary.cultural_tips} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Create ProgressCards**

`frontend/src/components/ProgressCards.jsx`:
```jsx
import { Cloud, ArrowLeftRight, BookOpen, Database, FileText, Loader2, CheckCircle2 } from "lucide-react";

const STEP_CONFIG = {
  weather: { icon: Cloud, label: "Weather Forecast" },
  currency: { icon: ArrowLeftRight, label: "Currency Rates" },
  wikipedia: { icon: BookOpen, label: "Destination Info" },
  rag: { icon: Database, label: "Travel Knowledge" },
  itinerary: { icon: FileText, label: "Building Itinerary" },
};

export default function ProgressCards({ progress }) {
  if (!progress || progress.length === 0) return null;

  return (
    <div className="max-w-lg mx-auto space-y-3">
      <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--color-primary)" }}>
        Researching your trip...
      </h2>
      {progress.map((p, i) => {
        const config = STEP_CONFIG[p.step] || { icon: Loader2, label: p.step };
        const Icon = config.icon;
        const isComplete = p.status === "complete";

        return (
          <div
            key={i}
            className="animate-fade-in flex items-center gap-3 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl px-4 py-3"
          >
            <Icon size={18} className={isComplete ? "text-green-600" : "text-[var(--color-accent)] animate-pulse"} />
            <span className="text-sm flex-1">{p.label || config.label}</span>
            {isComplete ? (
              <CheckCircle2 size={16} className="text-green-600" />
            ) : (
              <Loader2 size={16} className="text-[var(--color-accent)] animate-spin" />
            )}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 8: Update App.jsx to use real components**

Replace the itinerary placeholder and progress section in `frontend/src/App.jsx`. The right panel section (inside the `<div className="flex-1 ...">`) becomes:

```jsx
import ItineraryView from "./components/ItineraryView";
import ProgressCards from "./components/ProgressCards";
```

Update the right panel content in the return:
```jsx
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
```

- [ ] **Step 9: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/ frontend/src/App.jsx
git commit -m "feat: itinerary view, day cards, weather badges, progress cards, sidebar widgets"
```

---

### Task 14: Containerfiles

**Files:**
- Create: `backend/Containerfile`
- Create: `frontend/Containerfile`
- Create: `frontend/nginx.conf`
- Create: `mcp/currency/Containerfile`
- Create: `mcp/weather/Containerfile`
- Create: `mcp/wikipedia/Containerfile`

- [ ] **Step 1: Create backend Containerfile**

`backend/Containerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

COPY alembic/ alembic/
COPY alembic/alembic.ini .

EXPOSE 8000

CMD ["python", "-m", "smart_travel_buddy"]
```

- [ ] **Step 2: Create frontend Containerfile and nginx config**

`frontend/nginx.conf`:
```nginx
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    location /health {
        proxy_pass http://backend:8000;
    }
}
```

`frontend/Containerfile`:
```dockerfile
FROM node:20-slim AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: Create MCP Containerfiles**

`mcp/currency/Containerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "mcp_currency"]
```

`mcp/weather/Containerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "mcp_weather"]
```

`mcp/wikipedia/Containerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "mcp_wikipedia"]
```

- [ ] **Step 4: Verify backend image builds**

```bash
cd backend && podman build -t smart-travel-buddy-backend -f Containerfile .
```

Expected: Image builds successfully.

- [ ] **Step 5: Commit**

```bash
git add backend/Containerfile frontend/Containerfile frontend/nginx.conf \
       mcp/currency/Containerfile mcp/weather/Containerfile mcp/wikipedia/Containerfile
git commit -m "feat: Containerfiles for all services"
```

---

### Task 15: GitOps Manifests

**Files:**
- Create: `gitops/base/namespace.yaml`
- Create: `gitops/base/kustomization.yaml`
- Create: `gitops/base/postgresql/` (deployment, service, pvc, kustomization)
- Create: `gitops/base/backend/` (deployment, service, kustomization)
- Create: `gitops/base/frontend/` (deployment, service, kustomization)
- Create: `gitops/base/mcp-weather/` (deployment, service, kustomization)
- Create: `gitops/base/mcp-currency/` (deployment, service, kustomization)
- Create: `gitops/base/mcp-wikipedia/` (deployment, service, kustomization)
- Create: `gitops/overlays/dev/` (kustomization, configmap)

**Depends on:** Task 14 (Containerfiles)

- [ ] **Step 1: Create namespace and base kustomization**

`gitops/base/namespace.yaml`:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: smart-travel-buddy
```

`gitops/base/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  - postgresql
  - mcp-currency
  - mcp-weather
  - mcp-wikipedia
  - backend
  - frontend
```

- [ ] **Step 2: Create PostgreSQL manifests**

`gitops/base/postgresql/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
  - pvc.yaml
```

`gitops/base/postgresql/pvc.yaml`:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgresql-data
  namespace: smart-travel-buddy
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

`gitops/base/postgresql/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgresql
  namespace: smart-travel-buddy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgresql
  template:
    metadata:
      labels:
        app: postgresql
    spec:
      containers:
        - name: postgresql
          image: pgvector/pgvector:pg16
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: travel_agent_db
            - name: POSTGRES_USER
              value: postgres
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgresql-secret
                  key: password
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              memory: 256Mi
              cpu: 100m
            limits:
              memory: 512Mi
              cpu: 500m
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: postgresql-data
```

`gitops/base/postgresql/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: postgresql
  namespace: smart-travel-buddy
spec:
  selector:
    app: postgresql
  ports:
    - port: 5432
      targetPort: 5432
```

- [ ] **Step 3: Create MCP manifests (all three)**

`gitops/base/mcp-currency/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

`gitops/base/mcp-currency/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-currency
  namespace: smart-travel-buddy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-currency
  template:
    metadata:
      labels:
        app: mcp-currency
    spec:
      containers:
        - name: mcp-currency
          image: smart-travel-buddy/mcp-currency:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: 64Mi
              cpu: 50m
            limits:
              memory: 128Mi
              cpu: 200m
```

`gitops/base/mcp-currency/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-currency
  namespace: smart-travel-buddy
spec:
  selector:
    app: mcp-currency
  ports:
    - port: 8000
      targetPort: 8000
```

`gitops/base/mcp-weather/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

`gitops/base/mcp-weather/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-weather
  namespace: smart-travel-buddy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-weather
  template:
    metadata:
      labels:
        app: mcp-weather
    spec:
      containers:
        - name: mcp-weather
          image: smart-travel-buddy/mcp-weather:latest
          ports:
            - containerPort: 8000
          env:
            - name: OPENWEATHERMAP_API_KEY
              valueFrom:
                secretKeyRef:
                  name: api-keys
                  key: openweathermap
          resources:
            requests:
              memory: 64Mi
              cpu: 50m
            limits:
              memory: 128Mi
              cpu: 200m
```

`gitops/base/mcp-weather/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-weather
  namespace: smart-travel-buddy
spec:
  selector:
    app: mcp-weather
  ports:
    - port: 8000
      targetPort: 8000
```

`gitops/base/mcp-wikipedia/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

`gitops/base/mcp-wikipedia/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-wikipedia
  namespace: smart-travel-buddy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-wikipedia
  template:
    metadata:
      labels:
        app: mcp-wikipedia
    spec:
      containers:
        - name: mcp-wikipedia
          image: smart-travel-buddy/mcp-wikipedia:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: 64Mi
              cpu: 50m
            limits:
              memory: 128Mi
              cpu: 200m
```

`gitops/base/mcp-wikipedia/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-wikipedia
  namespace: smart-travel-buddy
spec:
  selector:
    app: mcp-wikipedia
  ports:
    - port: 8000
      targetPort: 8000
```

- [ ] **Step 4: Create backend manifests**

`gitops/base/backend/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

`gitops/base/backend/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: smart-travel-buddy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: smart-travel-buddy/backend:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              value: "postgresql+asyncpg://postgres:$(POSTGRES_PASSWORD)@postgresql:5432/travel_agent_db"
            - name: DATABASE_URL_SYNC
              value: "postgresql+psycopg://postgres:$(POSTGRES_PASSWORD)@postgresql:5432/travel_agent_db"
            - name: MCP_WEATHER_URL
              value: "http://mcp-weather:8000/sse"
            - name: MCP_CURRENCY_URL
              value: "http://mcp-currency:8000/sse"
            - name: MCP_WIKIPEDIA_URL
              value: "http://mcp-wikipedia:8000/sse"
            - name: LLM_MODEL
              valueFrom:
                configMapKeyRef:
                  name: backend-config
                  key: llm-model
            - name: LLM_BASE_URL
              valueFrom:
                configMapKeyRef:
                  name: backend-config
                  key: llm-base-url
            - name: LLM_API_KEY
              valueFrom:
                secretKeyRef:
                  name: api-keys
                  key: llm-api-key
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgresql-secret
                  key: password
          resources:
            requests:
              memory: 512Mi
              cpu: 200m
            limits:
              memory: 1Gi
              cpu: 1000m
```

`gitops/base/backend/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: smart-travel-buddy
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
```

- [ ] **Step 5: Create frontend manifests**

`gitops/base/frontend/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
```

`gitops/base/frontend/deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: smart-travel-buddy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: smart-travel-buddy/frontend:latest
          ports:
            - containerPort: 8080
          resources:
            requests:
              memory: 64Mi
              cpu: 50m
            limits:
              memory: 128Mi
              cpu: 200m
```

`gitops/base/frontend/service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: smart-travel-buddy
spec:
  selector:
    app: frontend
  ports:
    - port: 8080
      targetPort: 8080
```

- [ ] **Step 6: Create dev overlay**

`gitops/overlays/dev/kustomization.yaml`:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

patches:
  - target:
      kind: Deployment
      name: backend
    patch: |
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value:
          name: DEBUG
          value: "true"

configMapGenerator:
  - name: backend-config
    namespace: smart-travel-buddy
    literals:
      - llm-model=gpt-4o
      - llm-base-url=https://api.openai.com/v1
```

`gitops/overlays/dev/configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: smart-travel-buddy
data:
  llm-model: "gpt-4o"
  llm-base-url: "https://api.openai.com/v1"
```

- [ ] **Step 7: Validate kustomize build**

```bash
kustomize build gitops/overlays/dev/
```

Expected: Valid YAML output with all resources.

- [ ] **Step 8: Commit**

```bash
git add gitops/
git commit -m "feat: Kustomize GitOps manifests for all services"
```

---

### Task 16: Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create the Makefile**

`Makefile`:
```makefile
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
		-p 8002:8000 \
		$(REGISTRY)/smart-travel-buddy-mcp-currency:$(TAG)

run-mcp-weather:
	$(PODMAN) run -d --name stb-mcp-weather --network $(NETWORK) \
		-e OPENWEATHERMAP_API_KEY=$(OPENWEATHERMAP_API_KEY) \
		-p 8001:8000 \
		$(REGISTRY)/smart-travel-buddy-mcp-weather:$(TAG)

run-mcp-wikipedia:
	$(PODMAN) run -d --name stb-mcp-wikipedia --network $(NETWORK) \
		-p 8003:8000 \
		$(REGISTRY)/smart-travel-buddy-mcp-wikipedia:$(TAG)

run-backend:
	$(PODMAN) run -d --name stb-backend --network $(NETWORK) \
		-e DATABASE_URL=postgresql+asyncpg://postgres:postgres@stb-postgresql:5432/travel_agent_db \
		-e DATABASE_URL_SYNC=postgresql+psycopg://postgres:postgres@stb-postgresql:5432/travel_agent_db \
		-e MCP_WEATHER_URL=http://stb-mcp-weather:8000/sse \
		-e MCP_CURRENCY_URL=http://stb-mcp-currency:8000/sse \
		-e MCP_WIKIPEDIA_URL=http://stb-mcp-wikipedia:8000/sse \
		-e LLM_MODEL=$(LLM_MODEL) \
		-e LLM_BASE_URL=$(LLM_BASE_URL) \
		-e LLM_API_KEY=$(LLM_API_KEY) \
		-e DEBUG=true \
		-p 8000:8000 \
		$(REGISTRY)/smart-travel-buddy-backend:$(TAG)

run-frontend:
	@echo "Starting frontend dev server (not containerized for hot reload)..."
	cd frontend && npm run dev &

# ── Database ─────────────────────────────────────────────────────

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m smart_travel_buddy.rag.seed ../../knowledge

# ── Test & Lint ──────────────────────────────────────────────────

test:
	cd backend && python -m pytest tests/ -v
	cd mcp/currency && python -m pytest tests/ -v
	cd mcp/weather && python -m pytest tests/ -v
	cd mcp/wikipedia && python -m pytest tests/ -v

lint:
	cd backend && ruff check . && ruff format --check .

# ── Deploy ───────────────────────────────────────────────────────

deploy:
	oc apply -k gitops/overlays/dev/

# ── Cleanup ──────────────────────────────────────────────────────

stop:
	$(PODMAN) stop stb-postgresql stb-mcp-currency stb-mcp-weather stb-mcp-wikipedia stb-backend 2>/dev/null || true
	$(PODMAN) rm stb-postgresql stb-mcp-currency stb-mcp-weather stb-mcp-wikipedia stb-backend 2>/dev/null || true

clean: stop
	$(PODMAN) network rm $(NETWORK) 2>/dev/null || true
	$(PODMAN) rmi $(addprefix $(REGISTRY)/smart-travel-buddy-,$(addsuffix :$(TAG),$(IMAGES))) 2>/dev/null || true
```

- [ ] **Step 2: Verify Makefile syntax**

```bash
make -n build
```

Expected: Shows the podman build commands without executing them.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: Makefile for build, run, test, deploy workflows"
```

---

## Self-Review Results

**Spec coverage check:**
- User experience flow (interview → research → itinerary → refinement): Tasks 9, 10, 11 ✓
- Architecture (FastAPI + LangGraph + MCPs + RAG + PostgreSQL): Tasks 1-2, 6, 8, 10-11 ✓
- MCP servers (weather, currency, Wikipedia as standalone pods): Tasks 3-5 ✓
- RAG knowledge base with pgvector: Tasks 6-7 ✓
- Frontend (chat, thinking bubbles, itinerary cards, progress, widgets): Tasks 12-13 ✓
- Database (sessions, messages, knowledge_chunks, itineraries): Task 2 ✓
- LLM configuration (ChatOpenAI, swappable via env): Task 1, 11 ✓
- Containerfiles: Task 14 ✓
- GitOps (Kustomize, ArgoCD-ready): Task 15 ✓
- Makefile (no docker-compose): Task 16 ✓
- Thinking mode support: Task 12 (ThinkingBubble, MessageBubble parsing) ✓
- MCP SSE transport: Tasks 3-5 (__main__.py), Task 11 (orchestrator client) ✓

**Placeholder scan:** No TBDs, TODOs, or "implement later" found.

**Type consistency check:**
- `TravelState` used consistently across interview.py, research.py, itinerary.py, orchestrator.py ✓
- `broadcast(event_type, data)` signature consistent across ws/handler.py and all graph nodes ✓
- MCP tool categorization in orchestrator matches tool names in MCP servers ✓
- Frontend event types match backend broadcast calls ✓
