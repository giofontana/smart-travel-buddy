"""NeMo Guardrails client using the /v1/guardrail/checks endpoint.

The checks endpoint validates messages against the configured rails without generating an LLM
response: user messages go through the input rails, assistant messages through the output rails.
Inference itself still goes directly to the model.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from smart_travel_buddy.config import settings

logger = logging.getLogger(__name__)

INPUT_REFUSAL = (
    "I can't help with that request. Please don't share personal data such as emails or "
    "card numbers, and keep the conversation about your trip."
)
OUTPUT_REFUSAL = (
    "I couldn't produce an itinerary that passed the safety checks. "
    "Please try rephrasing your request."
)


@dataclass
class GuardrailResult:
    blocked: bool
    rails: list[str] = field(default_factory=list)
    error: str | None = None


def is_guardrails_available() -> bool:
    return bool(settings.guardrails_url)


def _auth_headers() -> dict[str, str]:
    try:
        token = Path(settings.guardrails_token_file).read_text().strip()
    except OSError:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _failure(error: str) -> GuardrailResult:
    logger.warning(f"NeMo Guardrails check failed: {error}")
    return GuardrailResult(blocked=not settings.guardrails_fail_open, error=error)


async def check(
    messages: list[dict], transport: httpx.AsyncBaseTransport | None = None
) -> GuardrailResult:
    """Check messages ({"role": ..., "content": ...}) against the NeMo Guardrails rails."""
    url = f"{settings.guardrails_url.rstrip('/')}/v1/guardrail/checks"
    payload = {"model": settings.llm_model, "messages": messages}

    try:
        # trust_env=True picks up SSL_CERT_FILE, which includes the OpenShift service CA.
        async with httpx.AsyncClient(
            timeout=settings.guardrails_timeout, transport=transport, trust_env=True
        ) as client:
            response = await client.post(url, json=payload, headers=_auth_headers())
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as e:
        return _failure(str(e))

    status = body.get("status")
    if status == "error":
        return _failure(f"guardrails returned an error: {body}")

    rails = (body.get("guardrails_data") or {}).get("log", {}).get("activated_rails") or [
        name for name, result in (body.get("rails_status") or {}).items()
        if result.get("status") == "blocked"
    ]
    return GuardrailResult(blocked=status == "blocked", rails=rails)
