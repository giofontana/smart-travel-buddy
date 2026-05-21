"""Tests for currency MCP server."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.asyncio
async def test_get_exchange_rate():
    """Test get_exchange_rate tool returns correct rate information."""
    from mcp_currency.server import get_exchange_rate

    mock_response_data = {
        "base": "USD",
        "date": "2026-05-21",
        "rates": {"JPY": 149.5}
    }

    mock_response = Mock()
    mock_response.json.return_value = mock_response_data

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await get_exchange_rate("USD", "JPY")
        result_data = json.loads(result)

        assert "from" in result_data
        assert result_data["from"] == "USD"
        assert "to" in result_data
        assert result_data["to"] == "JPY"
        assert "rate" in result_data
        assert result_data["rate"] == 149.5
        assert "date" in result_data
        assert result_data["date"] == "2026-05-21"


@pytest.mark.asyncio
async def test_convert():
    """Test convert tool returns correct conversion information."""
    from mcp_currency.server import convert

    mock_response_data = {
        "amount": 100.0,
        "base": "USD",
        "date": "2026-05-21",
        "rates": {"JPY": 14950.0}
    }

    mock_response = Mock()
    mock_response.json.return_value = mock_response_data

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await convert(100.0, "USD", "JPY")
        result_data = json.loads(result)

        assert "amount" in result_data
        assert result_data["amount"] == 100.0
        assert "from" in result_data
        assert result_data["from"] == "USD"
        assert "to" in result_data
        assert result_data["to"] == "JPY"
        assert "converted" in result_data
        assert result_data["converted"] == 14950.0
        assert "rate" in result_data
        assert "date" in result_data
        assert result_data["date"] == "2026-05-21"
