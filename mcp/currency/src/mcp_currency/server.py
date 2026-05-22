"""Currency MCP server using Frankfurter API."""

import json

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("currency", host="0.0.0.0")


@mcp.tool()
async def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """
    Get the current exchange rate between two currencies.

    Args:
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "JPY")

    Returns:
        JSON string containing from, to, rate, and date
    """
    url = f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        data = response.json()

        if "rates" not in data:
            return json.dumps({"error": data.get("message", "Unknown error"), "from": from_currency, "to": to_currency})

        result = {
            "from": data["base"],
            "to": to_currency,
            "rate": data["rates"][to_currency],
            "date": data["date"]
        }

        return json.dumps(result)


@mcp.tool()
async def convert(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Convert an amount from one currency to another.

    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "JPY")

    Returns:
        JSON string containing amount, from, to, converted, rate, and date
    """
    url = f"https://api.frankfurter.app/latest?amount={amount}&from={from_currency}&to={to_currency}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        data = response.json()

        converted_amount = data["rates"][to_currency]
        rate = converted_amount / amount

        result = {
            "amount": data["amount"],
            "from": data["base"],
            "to": to_currency,
            "converted": converted_amount,
            "rate": rate,
            "date": data["date"]
        }

        return json.dumps(result)
