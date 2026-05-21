"""Entry point for running the Smart Travel Buddy server."""

import uvicorn

from smart_travel_buddy.config import settings


def main() -> None:
    """Run the FastAPI application with uvicorn."""
    uvicorn.run(
        "smart_travel_buddy.server:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
