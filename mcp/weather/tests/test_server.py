"""Tests for weather MCP server."""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from mcp_weather.server import get_current_weather, get_forecast


@pytest.fixture(autouse=True)
def mock_env_var():
    """Set OPENWEATHERMAP_API_KEY for all tests."""
    os.environ["OPENWEATHERMAP_API_KEY"] = "test_api_key_12345"
    yield
    os.environ.pop("OPENWEATHERMAP_API_KEY", None)


@pytest.fixture
def mock_forecast_response():
    """Mock OpenWeatherMap forecast API response."""
    return {
        "city": {"name": "Paris"},
        "cnt": 40,
        "list": [
            # Day 1 - 2024-01-15
            {
                "dt_txt": "2024-01-15 00:00:00",
                "main": {"temp_min": 5.0, "temp_max": 8.0, "humidity": 80},
                "weather": [{"main": "Clear", "icon": "01d"}],
                "wind": {"speed": 3.5}
            },
            {
                "dt_txt": "2024-01-15 03:00:00",
                "main": {"temp_min": 4.0, "temp_max": 7.0, "humidity": 82},
                "weather": [{"main": "Clear", "icon": "01d"}],
                "wind": {"speed": 3.2}
            },
            {
                "dt_txt": "2024-01-15 06:00:00",
                "main": {"temp_min": 6.0, "temp_max": 9.0, "humidity": 78},
                "weather": [{"main": "Clouds", "icon": "02d"}],
                "wind": {"speed": 4.0}
            },
            # Day 2 - 2024-01-16
            {
                "dt_txt": "2024-01-16 00:00:00",
                "main": {"temp_min": 7.0, "temp_max": 11.0, "humidity": 75},
                "weather": [{"main": "Rain", "icon": "10d"}],
                "wind": {"speed": 5.0}
            },
            {
                "dt_txt": "2024-01-16 03:00:00",
                "main": {"temp_min": 8.0, "temp_max": 12.0, "humidity": 73},
                "weather": [{"main": "Rain", "icon": "10d"}],
                "wind": {"speed": 5.5}
            },
        ]
    }


@pytest.fixture
def mock_current_weather_response():
    """Mock OpenWeatherMap current weather API response."""
    return {
        "name": "Paris",
        "sys": {"country": "FR"},
        "main": {
            "temp": 15.5,
            "humidity": 65
        },
        "weather": [
            {"main": "Clear", "icon": "01d"}
        ],
        "wind": {
            "speed": 4.2
        }
    }


@pytest.mark.asyncio
async def test_get_forecast(mock_forecast_response):
    """Test get_forecast aggregates daily data correctly."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_response = AsyncMock()
        mock_response.json.return_value = mock_forecast_response
        mock_instance.get.return_value = mock_response

        result_str = await get_forecast("Paris", "FR", days=2)
        result = json.loads(result_str)

        # Verify structure
        assert result["city"] == "Paris"
        assert result["country"] == "FR"
        assert "forecast" in result

        # Verify daily aggregation
        forecast = result["forecast"]
        assert len(forecast) == 2  # 2 days

        # Day 1 should aggregate min/max temps from multiple entries
        day1 = forecast[0]
        assert day1["date"] == "2024-01-15"
        assert day1["temp_min"] == 4.0  # min from all day 1 entries
        assert day1["temp_max"] == 9.0  # max from all day 1 entries
        assert "humidity" in day1
        assert "condition" in day1
        assert "icon" in day1
        assert "wind_speed" in day1

        # Day 2
        day2 = forecast[1]
        assert day2["date"] == "2024-01-16"
        assert day2["temp_min"] == 7.0
        assert day2["temp_max"] == 12.0


@pytest.mark.asyncio
async def test_get_current_weather(mock_current_weather_response):
    """Test get_current_weather returns correct format."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_response = AsyncMock()
        mock_response.json.return_value = mock_current_weather_response
        mock_instance.get.return_value = mock_response

        result_str = await get_current_weather("Paris", "FR")
        result = json.loads(result_str)

        # Verify all required fields
        assert result["city"] == "Paris"
        assert result["country"] == "FR"
        assert result["temperature"] == 15.5
        assert result["humidity"] == 65
        assert result["condition"] == "Clear"
        assert result["icon"] == "01d"
        assert result["wind_speed"] == 4.2


@pytest.mark.asyncio
async def test_get_forecast_default_days():
    """Test get_forecast with default days parameter."""
    mock_response = {
        "city": {"name": "London"},
        "list": []
    }

    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance

        mock_resp = AsyncMock()
        mock_resp.json.return_value = mock_response
        mock_instance.get.return_value = mock_resp

        result_str = await get_forecast("London", "GB")
        result = json.loads(result_str)

        # Verify the API was called with cnt=40 (5 days * 8 intervals)
        mock_instance.get.assert_called_once()
        call_url = mock_instance.get.call_args[0][0]
        assert "cnt=40" in call_url


@pytest.mark.asyncio
async def test_missing_api_key():
    """Test that missing API key raises ValueError."""
    os.environ.pop("OPENWEATHERMAP_API_KEY", None)

    from importlib import reload
    from mcp_weather import server
    reload(server)

    with pytest.raises(ValueError, match="OPENWEATHERMAP_API_KEY"):
        await server.get_current_weather("Paris", "FR")
