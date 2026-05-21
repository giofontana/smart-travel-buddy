"""Entry point for Wikipedia MCP server."""

from mcp_wikipedia.server import mcp

mcp.run(transport="sse")
