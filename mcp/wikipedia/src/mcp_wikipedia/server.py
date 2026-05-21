"""Wikipedia MCP server implementation."""

import json
import re

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("wikipedia")

# Constants
USER_AGENT = "SmartTravelBuddy/1.0"
SUMMARY_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
SEARCH_API = "https://en.wikipedia.org/w/rest.php/v1/search/page"


@mcp.tool()
async def get_summary(topic: str) -> str:
    """Get Wikipedia summary for a topic.

    Args:
        topic: The topic to get a summary for

    Returns:
        JSON string with title, description, extract, and thumbnail
    """
    url = SUMMARY_API.format(topic=topic)

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        )
        response.raise_for_status()
        data = response.json()

    # Extract required fields
    result = {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "extract": data.get("extract", ""),
        "thumbnail": data.get("thumbnail", {}).get("source", ""),
    }

    return json.dumps(result)


@mcp.tool()
async def search(query: str, limit: int = 5) -> str:
    """Search Wikipedia for articles matching a query.

    Args:
        query: The search query
        limit: Maximum number of results to return (default: 5)

    Returns:
        JSON string with query and list of results
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            SEARCH_API,
            params={"q": query, "limit": limit},
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()

    # Process results
    results = []
    for page in data.get("pages", []):
        # Clean HTML tags from excerpt
        excerpt = page.get("excerpt", "")
        # Remove <span class="searchmatch"> tags
        excerpt = re.sub(r'<span class="searchmatch">', "", excerpt)
        excerpt = re.sub(r"</span>", "", excerpt)

        results.append(
            {
                "title": page.get("title", ""),
                "excerpt": excerpt,
                "thumbnail": page.get("thumbnail", {}).get("url", ""),
            }
        )

    result = {"query": query, "results": results}

    return json.dumps(result)
