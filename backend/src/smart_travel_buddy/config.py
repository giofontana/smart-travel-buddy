"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = False
    port: int = 8000

    # Database settings
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/travel_agent_db"
    database_url_sync: str = "postgresql+psycopg://postgres:postgres@localhost:5432/travel_agent_db"

    # LLM settings
    llm_model: str = "gpt-4o"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = "sk-placeholder"

    # MCP server URLs
    mcp_weather_url: str = "http://localhost:8001/sse"
    mcp_currency_url: str = "http://localhost:8002/sse"
    mcp_wikipedia_url: str = "http://localhost:8003/sse"

    # External API keys
    openweathermap_api_key: str = ""

    # MLflow settings (optional - disabled when tracking_uri is empty)
    mlflow_tracking_uri: str = ""
    mlflow_experiment_name: str = "smart-travel-buddy"
    mlflow_tracking_auth: str = ""
    mlflow_tracking_token: str = ""
    mlflow_workspace: str = ""

    # LLM token cost per 1M tokens (USD)
    llm_input_token_cost: float = 1.0
    llm_output_token_cost: float = 3.0

    model_config = {
        "env_file": ".env",
    }


settings = Settings()
