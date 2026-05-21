"""Currency MCP server entry point."""

from mcp_currency.server import mcp

mcp.run(transport="sse")
