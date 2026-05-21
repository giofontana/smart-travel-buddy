"""Tests for application configuration."""

from smart_travel_buddy.config import Settings


def test_default_settings():
    """Test that default settings are loaded correctly."""
    settings = Settings(_env_file=None)

    assert settings.debug is False
    assert settings.port == 8000
    assert settings.database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/travel_agent_db"
    assert settings.database_url_sync == "postgresql+psycopg://postgres:postgres@localhost:5432/travel_agent_db"
    assert settings.llm_model == "gpt-4o"
    assert settings.llm_base_url == "https://api.openai.com/v1"
    assert settings.llm_api_key == "sk-placeholder"
    assert settings.mcp_weather_url == "http://localhost:8001/sse"
    assert settings.mcp_currency_url == "http://localhost:8002/sse"
    assert settings.mcp_wikipedia_url == "http://localhost:8003/sse"
    assert settings.openweathermap_api_key == ""


def test_settings_override(monkeypatch):
    """Test that environment variables override default settings."""
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("LLM_MODEL", "gpt-4-turbo")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-weather-key")

    settings = Settings(_env_file=None)

    assert settings.debug is True
    assert settings.port == 9000
    assert settings.llm_model == "gpt-4-turbo"
    assert settings.llm_api_key == "sk-test-key"
    assert settings.openweathermap_api_key == "test-weather-key"
