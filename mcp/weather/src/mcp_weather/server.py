"""Weather MCP server using OpenWeatherMap API."""

import json
import os
from collections import defaultdict
from datetime import datetime

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather", host="0.0.0.0")


def _get_api_key() -> str:
    """Get OpenWeatherMap API key from environment variable.

    Returns:
        API key string

    Raises:
        ValueError: If OPENWEATHERMAP_API_KEY environment variable is not set
    """
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENWEATHERMAP_API_KEY environment variable is required. "
            "Get your API key from https://openweathermap.org/api"
        )
    return api_key


@mcp.tool()
async def get_forecast(city: str, country_code: str, days: int = 5) -> str:
    """
    Get weather forecast for a city.

    Args:
        city: City name (e.g., "Paris")
        country_code: ISO 3166 country code (e.g., "FR")
        days: Number of days to forecast (1-5, default: 5)

    Returns:
        JSON string containing city, country, and daily forecast data
    """
    api_key = _get_api_key()

    # OpenWeatherMap returns forecast in 3-hour intervals
    # Each day has 8 intervals (24 hours / 3 hours)
    cnt = days * 8

    url = (
        f"https://api.openweathermap.org/data/2.5/forecast?"
        f"q={city},{country_code}&appid={api_key}&units=metric&cnt={cnt}"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

        # Aggregate 3-hour data into daily summaries
        daily_data = defaultdict(lambda: {
            "temps": [],
            "humidities": [],
            "conditions": [],
            "icons": [],
            "wind_speeds": []
        })

        for item in data.get("list", []):
            # Extract date from datetime string (e.g., "2024-01-15 00:00:00" -> "2024-01-15")
            dt_txt = item["dt_txt"]
            date = dt_txt.split(" ")[0]

            # Collect data for this date
            daily_data[date]["temps"].extend([
                item["main"]["temp_min"],
                item["main"]["temp_max"]
            ])
            daily_data[date]["humidities"].append(item["main"]["humidity"])
            daily_data[date]["conditions"].append(item["weather"][0]["main"])
            daily_data[date]["icons"].append(item["weather"][0]["icon"])
            daily_data[date]["wind_speeds"].append(item["wind"]["speed"])

        # Build forecast array with daily aggregations
        forecast = []
        for date in sorted(daily_data.keys()):
            day_data = daily_data[date]

            # Take the most common condition and icon for the day
            most_common_condition = max(set(day_data["conditions"]),
                                       key=day_data["conditions"].count)
            most_common_icon = max(set(day_data["icons"]),
                                  key=day_data["icons"].count)

            forecast.append({
                "date": date,
                "temp_min": min(day_data["temps"]),
                "temp_max": max(day_data["temps"]),
                "humidity": sum(day_data["humidities"]) // len(day_data["humidities"]),
                "condition": most_common_condition,
                "icon": most_common_icon,
                "wind_speed": sum(day_data["wind_speeds"]) / len(day_data["wind_speeds"])
            })

        result = {
            "city": data["city"]["name"],
            "country": country_code,
            "forecast": forecast
        }

        return json.dumps(result)


@mcp.tool()
async def get_current_weather(city: str, country_code: str) -> str:
    """
    Get current weather for a city.

    Args:
        city: City name (e.g., "Paris")
        country_code: ISO 3166 country code (e.g., "FR")

    Returns:
        JSON string containing current weather data
    """
    api_key = _get_api_key()

    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"q={city},{country_code}&appid={api_key}&units=metric"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

        result = {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["main"],
            "icon": data["weather"][0]["icon"],
            "wind_speed": data["wind"]["speed"]
        }

        return json.dumps(result)
