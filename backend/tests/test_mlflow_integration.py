import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def disable_mlflow(monkeypatch):
    from smart_travel_buddy.config import settings
    monkeypatch.setattr(settings, "mlflow_tracking_uri", "")


@pytest.fixture
def enable_mlflow(monkeypatch):
    from smart_travel_buddy.config import settings
    monkeypatch.setattr(settings, "mlflow_tracking_uri", "http://localhost:5000")


class TestIsMLflowEnabled:
    def test_disabled_when_uri_empty(self, disable_mlflow):
        from smart_travel_buddy.mlflow_utils import is_mlflow_enabled
        assert not is_mlflow_enabled()

    def test_enabled_when_uri_set_and_mlflow_installed(self, enable_mlflow):
        import smart_travel_buddy.mlflow_utils as mod
        original = mod._MLFLOW_AVAILABLE
        mod._MLFLOW_AVAILABLE = True
        try:
            assert mod.is_mlflow_enabled()
        finally:
            mod._MLFLOW_AVAILABLE = original

    def test_disabled_when_mlflow_not_installed(self, enable_mlflow):
        import smart_travel_buddy.mlflow_utils as mod
        original = mod._MLFLOW_AVAILABLE
        mod._MLFLOW_AVAILABLE = False
        try:
            assert not mod.is_mlflow_enabled()
        finally:
            mod._MLFLOW_AVAILABLE = original


class TestConfigureMlflow:
    def test_noop_when_disabled(self, disable_mlflow):
        from smart_travel_buddy.mlflow_utils import configure_mlflow
        configure_mlflow()

    @patch("smart_travel_buddy.mlflow_utils.mlflow")
    def test_calls_autolog_when_enabled(self, mock_mlflow, enable_mlflow):
        import smart_travel_buddy.mlflow_utils as mod
        original = mod._MLFLOW_AVAILABLE
        mod._MLFLOW_AVAILABLE = True
        mock_mlflow.langchain = MagicMock()
        try:
            mod.configure_mlflow()
            mock_mlflow.set_tracking_uri.assert_called_once_with("http://localhost:5000")
            mock_mlflow.set_experiment.assert_called_once_with("smart-travel-buddy")
            mock_mlflow.langchain.autolog.assert_called_once()
        finally:
            mod._MLFLOW_AVAILABLE = original


class TestMlflowRunContext:
    def test_noop_when_disabled(self, disable_mlflow):
        from smart_travel_buddy.mlflow_utils import mlflow_run
        state = {"phase": "interview", "destination": "", "interests": []}
        with mlflow_run("test-session-id", state) as run:
            assert run is None

    @patch("smart_travel_buddy.mlflow_utils.mlflow")
    def test_creates_run_when_enabled(self, mock_mlflow, enable_mlflow):
        import smart_travel_buddy.mlflow_utils as mod
        original = mod._MLFLOW_AVAILABLE
        mod._MLFLOW_AVAILABLE = True

        mock_run = MagicMock()
        mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=mock_run)
        mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)

        try:
            state = {"phase": "interview", "destination": "Tokyo", "interests": ["food"]}
            with mod.mlflow_run("test-session-id-1234", state) as run:
                assert run == mock_run

            mock_mlflow.start_run.assert_called_once()
            mock_mlflow.log_params.assert_called_once()
            mock_mlflow.log_param.assert_called_once_with("interests", "food")
        finally:
            mod._MLFLOW_AVAILABLE = original


class TestMlflowSpanContext:
    def test_noop_when_disabled(self, disable_mlflow):
        from smart_travel_buddy.mlflow_utils import mlflow_span
        with mlflow_span("test-span") as span:
            assert span is None

    @patch("smart_travel_buddy.mlflow_utils.mlflow")
    def test_creates_span_when_enabled(self, mock_mlflow, enable_mlflow):
        import smart_travel_buddy.mlflow_utils as mod
        original = mod._MLFLOW_AVAILABLE
        mod._MLFLOW_AVAILABLE = True

        mock_span = MagicMock()
        mock_mlflow.start_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_mlflow.start_span.return_value.__exit__ = MagicMock(return_value=False)

        try:
            attrs = {"tool.name": "get_forecast", "tool.input.city": "Tokyo"}
            with mod.mlflow_span("mcp-weather", attributes=attrs) as span:
                assert span == mock_span

            mock_mlflow.start_span.assert_called_once_with(name="mcp-weather", span_type="TOOL")
            mock_span.set_attributes.assert_called_once_with(attrs)
        finally:
            mod._MLFLOW_AVAILABLE = original


class TestLogRunMetrics:
    def test_noop_when_disabled(self, disable_mlflow):
        from smart_travel_buddy.mlflow_utils import log_run_metrics
        log_run_metrics({"duration": 1.5})

    @patch("smart_travel_buddy.mlflow_utils.mlflow")
    def test_logs_metrics_when_enabled(self, mock_mlflow, enable_mlflow):
        import smart_travel_buddy.mlflow_utils as mod
        original = mod._MLFLOW_AVAILABLE
        mod._MLFLOW_AVAILABLE = True
        try:
            metrics = {"total_duration_s": 2.5, "message_count": 4.0}
            mod.log_run_metrics(metrics)
            mock_mlflow.log_metrics.assert_called_once_with(metrics)
        finally:
            mod._MLFLOW_AVAILABLE = original

    @patch("smart_travel_buddy.mlflow_utils.mlflow")
    def test_swallows_exceptions(self, mock_mlflow, enable_mlflow):
        import smart_travel_buddy.mlflow_utils as mod
        original = mod._MLFLOW_AVAILABLE
        mod._MLFLOW_AVAILABLE = True
        mock_mlflow.log_metrics.side_effect = RuntimeError("connection failed")
        try:
            mod.log_run_metrics({"duration": 1.0})
        finally:
            mod._MLFLOW_AVAILABLE = original


@pytest.mark.asyncio
async def test_research_weather_creates_mlflow_span(disable_mlflow):
    mock_tool = AsyncMock()
    mock_tool.name = "get_forecast"
    mock_tool.ainvoke.return_value = json.dumps({"city": "Tokyo", "forecast": []})

    state = {
        "messages": [], "destination": "Tokyo, Japan",
        "dates": {"start": "2026-07-10", "end": "2026-07-14"},
        "interests": ["food"], "budget": "mid-range", "constraints": [],
        "phase": "research", "research_results": {}, "itinerary": None,
    }

    broadcast = AsyncMock()
    config = {"configurable": {
        "mcp_tools": {"weather": [mock_tool]},
        "broadcast": broadcast,
        "trace": None,
    }}

    from smart_travel_buddy.graph.research import call_weather
    result = await call_weather(state, config)

    mock_tool.ainvoke.assert_called_once()
    assert "weather" in result["research_results"]
