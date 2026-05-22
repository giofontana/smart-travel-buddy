import json
from datetime import datetime
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from smart_travel_buddy.graph.state import TravelState


# Mapping of country names to currency codes
DESTINATION_CURRENCIES = {
    "japan": "JPY",
    "france": "EUR",
    "usa": "USD",
    "united states": "USD",
    "italy": "EUR",
    "uk": "GBP",
    "united kingdom": "GBP",
    "spain": "EUR",
    "thailand": "THB",
    "australia": "AUD",
    "south africa": "ZAR",
    "brazil": "BRL",
    "mexico": "MXN",
    "canada": "CAD",
    "china": "CNY",
    "india": "INR",
    "germany": "EUR",
    "portugal": "EUR",
    "greece": "EUR",
    "netherlands": "EUR",
    "belgium": "EUR",
    "austria": "EUR",
    "switzerland": "CHF",
    "sweden": "SEK",
    "norway": "NOK",
    "denmark": "DKK",
    "poland": "PLN",
    "czech republic": "CZK",
    "hungary": "HUF",
    "turkey": "TRY",
    "russia": "RUB",
    "south korea": "KRW",
    "singapore": "SGD",
    "malaysia": "MYR",
    "indonesia": "IDR",
    "philippines": "PHP",
    "vietnam": "VND",
    "argentina": "ARS",
    "chile": "CLP",
    "colombia": "COP",
    "peru": "PEN",
    "new zealand": "NZD",
    "egypt": "EGP",
    "morocco": "MAD",
    "israel": "ILS",
    "uae": "AED",
    "united arab emirates": "AED",
    "saudi arabia": "SAR",
}


def _guess_currency(destination: str) -> str:
    """
    Guess the currency code based on destination.

    Args:
        destination: Full destination string (e.g., "Tokyo, Japan")

    Returns:
        Currency code (e.g., "JPY"), defaults to "EUR"
    """
    destination_lower = destination.lower()

    # Check each country in our mapping
    for country, currency in DESTINATION_CURRENCIES.items():
        if country in destination_lower:
            return currency

    # Default to EUR if no match
    return "EUR"


US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
}

COUNTRY_CODES = {
    "japan": "JP", "france": "FR", "usa": "US", "united states": "US",
    "italy": "IT", "uk": "GB", "united kingdom": "GB", "spain": "ES",
    "thailand": "TH", "australia": "AU", "south africa": "ZA",
    "brazil": "BR", "mexico": "MX", "canada": "CA", "china": "CN",
    "india": "IN", "germany": "DE", "portugal": "PT", "greece": "GR",
    "netherlands": "NL", "belgium": "BE", "austria": "AT",
    "switzerland": "CH", "sweden": "SE", "norway": "NO", "denmark": "DK",
    "poland": "PL", "czech republic": "CZ", "hungary": "HU",
    "turkey": "TR", "russia": "RU", "south korea": "KR",
    "singapore": "SG", "malaysia": "MY", "indonesia": "ID",
    "philippines": "PH", "vietnam": "VN", "argentina": "AR",
    "chile": "CL", "colombia": "CO", "peru": "PE", "new zealand": "NZ",
    "egypt": "EG", "morocco": "MA", "israel": "IL",
    "uae": "AE", "united arab emirates": "AE", "saudi arabia": "SA",
}


def _extract_city(destination: str) -> tuple[str, str]:
    """
    Extract city and country code from destination string.

    Args:
        destination: Destination string (e.g., "Tokyo, Japan")

    Returns:
        Tuple of (city, country_code) where country_code is 2-letter uppercase
    """
    parts = destination.split(",")
    city = parts[0].strip()

    location = parts[1].strip().lower() if len(parts) > 1 else ""

    if location in US_STATES:
        return city, "US"

    for country, code in COUNTRY_CODES.items():
        if country in location:
            return city, code

    return city, "US"


async def call_weather(state: TravelState, config: RunnableConfig) -> dict[str, Any]:
    """
    Call weather MCP tool to get forecast for destination.

    Args:
        state: Current travel state
        config: Configuration dict with mcp_tools and broadcast

    Returns:
        Dict with updated research_results containing weather data
    """
    destination = state["destination"]
    dates = state["dates"]

    # Broadcast progress
    broadcast = config["configurable"]["broadcast"]
    await broadcast({
        "step": "weather",
        "status": "started",
        "label": f"Checking weather for {destination}..."
    })

    # Extract city and country
    city, country_code = _extract_city(destination)

    # Calculate number of days
    if dates:
        start_date = datetime.strptime(dates["start"], "%Y-%m-%d")
        end_date = datetime.strptime(dates["end"], "%Y-%m-%d")
        days = (end_date - start_date).days + 1
    else:
        days = 7  # Default to 7 days

    # Find weather tool
    weather_tools = config["configurable"]["mcp_tools"]["weather"]
    weather_tool = None
    for tool in weather_tools:
        if "forecast" in tool.name.lower():
            weather_tool = tool
            break

    # Call the tool
    result = None
    if weather_tool:
        tool_input = {
            "city": city,
            "country_code": country_code,
            "days": days
        }
        result = await weather_tool.ainvoke(tool_input)

    # Broadcast complete
    await broadcast({
        "step": "weather",
        "status": "completed",
        "label": f"Weather data retrieved for {destination}"
    })

    # Update research results
    return {
        "research_results": {
            **state["research_results"],
            "weather": result
        }
    }


async def call_currency(state: TravelState, config: RunnableConfig) -> dict[str, Any]:
    """
    Call currency MCP tool to get exchange rate.

    Args:
        state: Current travel state
        config: Configuration dict with mcp_tools and broadcast

    Returns:
        Dict with updated research_results containing currency data
    """
    destination = state["destination"]

    # Broadcast progress
    broadcast = config["configurable"]["broadcast"]
    await broadcast({
        "step": "currency",
        "status": "started",
        "label": f"Checking exchange rates for {destination}..."
    })

    # Guess currency
    to_currency = _guess_currency(destination)

    # Find currency tool
    currency_tools = config["configurable"]["mcp_tools"]["currency"]
    currency_tool = None
    for tool in currency_tools:
        if "exchange_rate" in tool.name.lower():
            currency_tool = tool
            break

    # Call the tool (skip if same currency)
    result = None
    if to_currency == "USD":
        result = json.dumps({"from": "USD", "to": "USD", "rate": 1.0, "date": "N/A"})
    elif currency_tool:
        tool_input = {
            "from_currency": "USD",
            "to_currency": to_currency
        }
        result = await currency_tool.ainvoke(tool_input)

    # Broadcast complete
    await broadcast({
        "step": "currency",
        "status": "completed",
        "label": f"Exchange rates retrieved for {destination}"
    })

    # Update research results
    return {
        "research_results": {
            **state["research_results"],
            "currency": result
        }
    }


async def call_wikipedia(state: TravelState, config: RunnableConfig) -> dict[str, Any]:
    """
    Call Wikipedia MCP tool to get destination summary.

    Args:
        state: Current travel state
        config: Configuration dict with mcp_tools and broadcast

    Returns:
        Dict with updated research_results containing Wikipedia data
    """
    destination = state["destination"]

    # Broadcast progress
    broadcast = config["configurable"]["broadcast"]
    await broadcast({
        "step": "wikipedia",
        "status": "started",
        "label": f"Gathering information about {destination}..."
    })

    # Extract city name
    city, _ = _extract_city(destination)

    # Find Wikipedia tool
    wikipedia_tools = config["configurable"]["mcp_tools"]["wikipedia"]
    wikipedia_tool = None
    for tool in wikipedia_tools:
        if "summary" in tool.name.lower():
            wikipedia_tool = tool
            break

    # Call the tool
    result = None
    if wikipedia_tool:
        tool_input = {
            "topic": city
        }
        result = await wikipedia_tool.ainvoke(tool_input)

    # Broadcast complete
    await broadcast({
        "step": "wikipedia",
        "status": "completed",
        "label": f"Information retrieved for {destination}"
    })

    # Update research results
    return {
        "research_results": {
            **state["research_results"],
            "wikipedia": result
        }
    }


async def call_rag(state: TravelState, config: RunnableConfig) -> dict[str, Any]:
    """
    Call RAG retriever to get relevant context from knowledge base.

    Args:
        state: Current travel state
        config: Configuration dict with optional db_session and broadcast

    Returns:
        Dict with updated research_results containing RAG context
    """
    destination = state["destination"]
    interests = state["interests"]

    # Broadcast progress
    broadcast = config["configurable"]["broadcast"]
    await broadcast({
        "step": "rag",
        "status": "started",
        "label": f"Searching knowledge base for {destination}..."
    })

    # Get db_session from config (optional)
    db_session = config.get("configurable", {}).get("db_session")

    rag_context = ""
    if db_session:
        try:
            # Import retriever
            from smart_travel_buddy.rag.retriever import retrieve_context

            # Build query from destination and interests
            query = f"{destination} {' '.join(interests)}"

            # Retrieve context
            chunks = await retrieve_context(db_session, query, k=5)
            rag_context = "\n\n".join(chunks)
        except Exception as e:
            # If RAG fails, continue without context
            rag_context = f"RAG retrieval failed: {str(e)}"

    # Broadcast complete
    await broadcast({
        "step": "rag",
        "status": "completed",
        "label": f"Knowledge base searched for {destination}"
    })

    # Update research results
    return {
        "research_results": {
            **state["research_results"],
            "rag_context": rag_context
        }
    }


def build_research_graph() -> StateGraph:
    """
    Build the research subgraph.

    Creates a sequential graph that:
    1. Calls weather API
    2. Calls currency API
    3. Calls Wikipedia API
    4. Calls RAG retriever
    5. Ends

    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(TravelState)

    # Add nodes
    workflow.add_node("weather", call_weather)
    workflow.add_node("currency", call_currency)
    workflow.add_node("wikipedia", call_wikipedia)
    workflow.add_node("rag", call_rag)

    # Set entry point
    workflow.set_entry_point("weather")

    # Add sequential edges
    workflow.add_edge("weather", "currency")
    workflow.add_edge("currency", "wikipedia")
    workflow.add_edge("wikipedia", "rag")
    workflow.add_edge("rag", END)

    return workflow.compile()
