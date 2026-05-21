"""Main entry point for weather MCP server."""

from mcp_weather.server import mcp

if __name__ == "__main__":
    mcp.run(transport="sse")
