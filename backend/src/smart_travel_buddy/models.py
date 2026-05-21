"""Database models using SQLModel."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    """Chat session tracking a user's travel planning conversation."""

    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    destination: str = Field(default="")
    status: str = Field(default="interview")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(SQLModel, table=True):
    """Individual message in a chat session."""

    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id")
    role: str
    content: str = Field(sa_column=Column(Text))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeChunk(SQLModel, table=True):
    """Knowledge base chunk with embeddings for RAG."""

    __tablename__ = "knowledge_chunks"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_file: str
    chunk_text: str = Field(sa_column=Column(Text))
    metadata_: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )
    # Note: embedding column is added via Alembic migration for pgvector
    # Not included in SQLModel to allow SQLite testing


class Itinerary(SQLModel, table=True):
    """Generated travel itinerary."""

    __tablename__ = "itineraries"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id")
    itinerary_json: dict[str, Any] = Field(sa_column=Column(JSON))
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
