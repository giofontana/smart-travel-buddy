"""Tests for Wikipedia MCP server."""

import json
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_summary():
    """Test get_summary tool with mocked Wikipedia API."""
    from mcp_wikipedia.server import get_summary

    # Mock Wikipedia API response
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "title": "Paris",
        "description": "Capital of France",
        "extract": "Paris is the capital and most populous city of France.",
        "thumbnail": {"source": "https://example.com/paris.jpg"},
    }
    mock_response.raise_for_status = lambda: None

    with patch("mcp_wikipedia.server.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_summary("Paris")
        result_data = json.loads(result)

        # Verify output fields
        assert result_data["title"] == "Paris"
        assert result_data["description"] == "Capital of France"
        assert result_data["extract"] == "Paris is the capital and most populous city of France."
        assert result_data["thumbnail"] == "https://example.com/paris.jpg"


@pytest.mark.asyncio
async def test_get_summary_no_thumbnail():
    """Test get_summary when no thumbnail is available."""
    from mcp_wikipedia.server import get_summary

    # Mock Wikipedia API response without thumbnail
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "title": "Test Topic",
        "description": "Test description",
        "extract": "Test extract content.",
    }
    mock_response.raise_for_status = lambda: None

    with patch("mcp_wikipedia.server.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_summary("Test")
        result_data = json.loads(result)

        # Verify thumbnail is empty string when not present
        assert result_data["thumbnail"] == ""


@pytest.mark.asyncio
async def test_search():
    """Test search tool with mocked Wikipedia API."""
    from mcp_wikipedia.server import search

    # Mock Wikipedia API response
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "pages": [
            {
                "title": "Paris",
                "excerpt": "Paris is the <span class=\"searchmatch\">capital</span> of France.",
                "thumbnail": {"url": "https://example.com/paris.jpg"},
            },
            {
                "title": "France",
                "excerpt": "France is a country in <span class=\"searchmatch\">Europe</span>.",
                "thumbnail": {"url": "https://example.com/france.jpg"},
            },
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("mcp_wikipedia.server.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search("capital", limit=5)
        result_data = json.loads(result)

        # Verify output structure
        assert result_data["query"] == "capital"
        assert len(result_data["results"]) == 2

        # Verify first result
        assert result_data["results"][0]["title"] == "Paris"
        # HTML tags should be removed
        assert "<span" not in result_data["results"][0]["excerpt"]
        assert result_data["results"][0]["excerpt"] == "Paris is the capital of France."
        assert result_data["results"][0]["thumbnail"] == "https://example.com/paris.jpg"

        # Verify second result
        assert result_data["results"][1]["title"] == "France"
        assert result_data["results"][1]["excerpt"] == "France is a country in Europe."
        assert result_data["results"][1]["thumbnail"] == "https://example.com/france.jpg"


@pytest.mark.asyncio
async def test_search_no_thumbnails():
    """Test search when results have no thumbnails."""
    from mcp_wikipedia.server import search

    # Mock Wikipedia API response without thumbnails
    mock_response = AsyncMock()
    mock_response.json = lambda: {
        "pages": [
            {
                "title": "Test Article",
                "excerpt": "Test content here.",
            },
        ]
    }
    mock_response.raise_for_status = lambda: None

    with patch("mcp_wikipedia.server.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search("test")
        result_data = json.loads(result)

        # Verify thumbnail is empty string when not present
        assert result_data["results"][0]["thumbnail"] == ""
