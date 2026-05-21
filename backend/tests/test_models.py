"""Tests for database models."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_travel_buddy.models import Itinerary, KnowledgeChunk, Message, Session


@pytest.mark.asyncio
async def test_create_session(async_session: AsyncSession):
    """Test creating a ChatSession with destination and status."""
    session = Session(destination="Tokyo, Japan", status="interview")

    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)

    # Verify id and created_at are set
    assert session.id is not None
    assert session.created_at is not None
    assert isinstance(session.created_at, datetime)
    assert session.destination == "Tokyo, Japan"
    assert session.status == "interview"


@pytest.mark.asyncio
async def test_create_message(async_session: AsyncSession):
    """Test creating a message with foreign key to session."""
    # Create session first
    session = Session(destination="Paris, France", status="interview")
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)

    # Create message with foreign key
    message = Message(
        session_id=session.id,
        role="user",
        content="I want to visit the Eiffel Tower",
    )
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Verify foreign key works
    assert message.id is not None
    assert message.session_id == session.id
    assert message.role == "user"
    assert message.content == "I want to visit the Eiffel Tower"
    assert message.timestamp is not None


@pytest.mark.asyncio
async def test_create_itinerary(async_session: AsyncSession):
    """Test creating an itinerary with JSONB data and version."""
    # Create session first
    session = Session(destination="Rome, Italy", status="planning")
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)

    # Create itinerary with JSONB data
    itinerary_data = {
        "days": [
            {
                "day": 1,
                "activities": [
                    {"time": "09:00", "activity": "Visit Colosseum"},
                    {"time": "14:00", "activity": "Visit Roman Forum"},
                ],
            }
        ]
    }

    itinerary = Itinerary(
        session_id=session.id,
        itinerary_json=itinerary_data,
        version=1,
    )
    async_session.add(itinerary)
    await async_session.commit()
    await async_session.refresh(itinerary)

    # Verify JSONB data and version
    assert itinerary.id is not None
    assert itinerary.session_id == session.id
    assert itinerary.itinerary_json == itinerary_data
    assert itinerary.version == 1
    assert itinerary.created_at is not None


@pytest.mark.asyncio
async def test_create_knowledge_chunk(async_session: AsyncSession):
    """Test creating a knowledge chunk with metadata."""
    chunk = KnowledgeChunk(
        source_file="travel_guide.pdf",
        chunk_text="Tokyo is the capital of Japan and one of the world's most vibrant cities.",
        metadata_={"page": 42, "section": "Asia"},
    )

    async_session.add(chunk)
    await async_session.commit()
    await async_session.refresh(chunk)

    # Verify data
    assert chunk.id is not None
    assert chunk.source_file == "travel_guide.pdf"
    assert "Tokyo is the capital" in chunk.chunk_text
    assert chunk.metadata_ == {"page": 42, "section": "Asia"}
