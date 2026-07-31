import time
import uuid
from typing import Any, Callable, Coroutine

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from smart_travel_buddy.config import settings
from smart_travel_buddy.graph.state import TravelState
from smart_travel_buddy.mlflow_utils import mlflow_run, log_run_metrics
from smart_travel_buddy.trace import TraceEmitter
from smart_travel_buddy.graph.interview import build_interview_graph, should_continue_interview
from smart_travel_buddy.graph.research import (
    call_weather,
    call_currency,
    call_wikipedia,
    call_rag,
)
from smart_travel_buddy.graph.itinerary import build_itinerary_graph, itinerary_node


BroadcastFn = Callable[[str, dict], Coroutine[Any, Any, None]]


class Orchestrator:
    def __init__(self, broadcast: BroadcastFn):
        self.session_id = str(uuid.uuid4())
        self.broadcast = broadcast
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
        self.memory = MemorySaver()
        self.interview_graph = build_interview_graph()
        self.itinerary_graph = build_itinerary_graph().compile()
        self.state: TravelState = {
            "messages": [],
            "destination": "",
            "dates": None,
            "interests": [],
            "budget": "",
            "constraints": [],
            "phase": "interview",
            "research_results": {},
            "itinerary": None,
        }
        self.mcp_client = None

    async def _broadcast_wrapper(self, event_type_or_dict, data=None):
        """
        Wrapper to handle both broadcast patterns:
        - Old pattern (research nodes): broadcast({"step": ..., "status": ...})
        - New pattern (itinerary nodes): broadcast("progress", {"step": ..., "status": ...})
        """
        if data is None and isinstance(event_type_or_dict, dict):
            # research nodes: broadcast({"step": ..., "status": ...})
            await self.broadcast("progress", event_type_or_dict)
        else:
            # itinerary nodes: broadcast("progress", {"step": ..., "status": ...})
            await self.broadcast(event_type_or_dict, data)

    async def _init_mcp_client(self):
        from langchain_mcp_adapters.client import MultiServerMCPClient

        self.mcp_client = MultiServerMCPClient(
            {
                "weather": {"url": settings.mcp_weather_url, "transport": "sse"},
                "currency": {"url": settings.mcp_currency_url, "transport": "sse"},
                "wikipedia": {"url": settings.mcp_wikipedia_url, "transport": "sse"},
            }
        )

    async def _get_mcp_tools(self) -> dict[str, list]:
        if not self.mcp_client:
            return {}
        all_tools = await self.mcp_client.get_tools()
        categorized = {"weather": [], "currency": [], "wikipedia": []}
        for tool in all_tools:
            name = tool.name.lower()
            if "forecast" in name or "weather" in name:
                categorized["weather"].append(tool)
            elif "exchange" in name or "convert" in name or "currency" in name:
                categorized["currency"].append(tool)
            elif "summary" in name or "search" in name or "wikipedia" in name:
                categorized["wikipedia"].append(tool)
        return categorized

    async def process_message(self, user_message: str):
        self.state["messages"] = list(self.state["messages"]) + [HumanMessage(content=user_message)]
        trace = TraceEmitter(self.broadcast)

        start_time = time.time()

        with mlflow_run(self.session_id, self.state, request=user_message) as span:
            await trace.start("user", "backend", f"Message received: {user_message[:50]}")

            if self.state["phase"] == "interview":
                await self._run_interview(trace)
            elif self.state["phase"] == "research":
                await self._run_research(trace)
                await self._run_itinerary(trace)
            elif self.state["phase"] == "refinement":
                await self._run_refinement(user_message, trace)

            await trace.end("backend", "user", "Response sent")

            if span:
                last_msg = self.state["messages"][-1]
                response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                import re
                think_match = re.search(r"<think>(.*?)</think>", response, flags=re.DOTALL)
                if think_match:
                    clean = re.sub(r"<think>.*?</think>\s*", "", response, flags=re.DOTALL)
                    span.set_outputs({
                        "choices": [{
                            "message": {
                                "role": "assistant",
                                "content": clean,
                                "reasoning": think_match.group(1).strip(),
                            }
                        }]
                    })
                else:
                    span.set_outputs({
                        "choices": [{
                            "message": {"role": "assistant", "content": response}
                        }]
                    })

            log_run_metrics({
                "total_duration_s": time.time() - start_time,
                "message_count": float(len(self.state["messages"])),
                "research_sources": float(len(self.state.get("research_results", {}))),
            })

    async def _run_interview(self, trace):
        config = {
            "configurable": {
                "llm": self.llm,
                "broadcast": self._broadcast_wrapper,
                "thread_id": self.session_id,
                "trace": trace,
            }
        }

        result = await self.interview_graph.ainvoke(self.state, config)
        self.state = {**self.state, **result}

        last_msg = self.state["messages"][-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        # Strip the JSON ready block from displayed message
        ready_idx = content.find('{"ready"')
        if ready_idx > 0:
            content = content[:ready_idx].rstrip()

        await self.broadcast("agent_message", {"content": content})

        if self.state["phase"] == "research":
            await self._run_research(trace)
            await self._run_itinerary(trace)

    async def _run_research(self, trace):
        await self.broadcast("phase_change", {"phase": "research"})

        if not self.mcp_client:
            await self._init_mcp_client()

        config = {
            "configurable": {
                "mcp_tools": await self._get_mcp_tools(),
                "broadcast": self._broadcast_wrapper,
                "db_session": None,
                "trace": trace,
            }
        }

        import asyncio

        weather_result, currency_result, wikipedia_result = await asyncio.gather(
            call_weather(self.state, config),
            call_currency(self.state, config),
            call_wikipedia(self.state, config),
        )

        self.state["research_results"] = {
            **weather_result.get("research_results", {}),
            **currency_result.get("research_results", {}),
            **wikipedia_result.get("research_results", {}),
        }

        rag_result = await call_rag(self.state, config)
        self.state["research_results"]["rag_context"] = rag_result["research_results"].get("rag_context", "")

    async def _run_itinerary(self, trace):
        config = {
            "configurable": {
                "llm": self.llm,
                "broadcast": self._broadcast_wrapper,
                "trace": trace,
            }
        }

        result = await self.itinerary_graph.ainvoke(self.state, config)
        self.state = {**self.state, **result}

    async def _run_refinement(self, user_message: str, trace):
        config = {
            "configurable": {
                "llm": self.llm,
                "broadcast": self._broadcast_wrapper,
                "trace": trace,
            }
        }

        result = await itinerary_node(self.state, config)
        self.state = {**self.state, **result}

    async def close(self):
        pass


async def create_orchestrator(broadcast: BroadcastFn) -> Orchestrator:
    return Orchestrator(broadcast)
