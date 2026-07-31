"""MLflow integration utilities with graceful degradation."""

import logging
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.langchain
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False
    mlflow = None


def is_mlflow_enabled() -> bool:
    from smart_travel_buddy.config import settings
    return _MLFLOW_AVAILABLE and bool(settings.mlflow_tracking_uri)


def configure_mlflow() -> None:
    if not is_mlflow_enabled():
        logger.info("MLflow tracing disabled (MLFLOW_TRACKING_URI not set or mlflow not installed)")
        return

    from smart_travel_buddy.config import settings

    if settings.mlflow_tracking_auth:
        os.environ.setdefault("MLFLOW_TRACKING_AUTH", settings.mlflow_tracking_auth)
    if settings.mlflow_tracking_token:
        os.environ.setdefault("MLFLOW_TRACKING_TOKEN", settings.mlflow_tracking_token)
    if settings.mlflow_workspace:
        os.environ.setdefault("MLFLOW_WORKSPACE", settings.mlflow_workspace)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

    # RHOAI MLflow requires auth on the workspace probe endpoint, but the SDK
    # sends the probe without workspace context, causing PERMISSION_DENIED.
    # Pre-set workspace support to skip the failing probe when workspace is configured.
    if settings.mlflow_workspace:
        try:
            store = mlflow.tracking.MlflowClient()._tracking_client.store
            if hasattr(store, "_workspace_support"):
                store._workspace_support = True
        except Exception:
            pass

    mlflow.set_experiment(settings.mlflow_experiment_name)
    mlflow.langchain.autolog()
    logger.info(f"MLflow tracing enabled: {settings.mlflow_tracking_uri}")


@contextmanager
def mlflow_run(session_id: str, state: dict, request: str = ""):
    if not is_mlflow_enabled():
        yield None
        return

    span_ctx = None
    root_span = None
    try:
        phase = state.get("phase", "unknown")
        run_name = f"session-{session_id[:8]}-{phase}"
        run_ctx = mlflow.start_run(run_name=run_name)
        run = run_ctx.__enter__()
        mlflow.log_params({
            "session_id": session_id,
            "phase": phase,
            "destination": state.get("destination", ""),
            "llm_model": _get_model_name(),
        })
        interests = state.get("interests")
        if interests:
            mlflow.log_param("interests", ", ".join(interests))
        span_ctx = mlflow.start_span(name=f"process_message:{phase}", span_type="CHAT_MODEL")
        root_span = span_ctx.__enter__()
        if request:
            root_span.set_inputs({"messages": [{"role": "user", "content": request}]})
        mlflow.update_current_trace(tags={"mlflow.trace.session": session_id})
    except Exception:
        logger.debug("MLflow run failed; continuing without tracing", exc_info=True)
        yield None
        return

    try:
        yield root_span
    finally:
        try:
            if span_ctx:
                span_ctx.__exit__(None, None, None)
        except Exception:
            logger.debug("MLflow root span cleanup failed", exc_info=True)
        try:
            run_ctx.__exit__(None, None, None)
        except Exception:
            logger.debug("MLflow run cleanup failed", exc_info=True)


@contextmanager
def mlflow_span(name: str, span_type: str = "TOOL", attributes: dict | None = None):
    if not is_mlflow_enabled():
        yield None
        return

    try:
        span_ctx = mlflow.start_span(name=name, span_type=span_type)
        span = span_ctx.__enter__()
        if attributes:
            span.set_attributes(attributes)
    except Exception:
        logger.debug("MLflow span '%s' failed; continuing without tracing", name, exc_info=True)
        yield None
        return

    try:
        yield span
    finally:
        try:
            span_ctx.__exit__(None, None, None)
        except Exception:
            logger.debug("MLflow span '%s' cleanup failed", name, exc_info=True)


def log_run_metrics(metrics: dict[str, float]) -> None:
    if not is_mlflow_enabled():
        return
    try:
        mlflow.log_metrics(metrics)
    except Exception:
        logger.debug("Failed to log MLflow metrics", exc_info=True)


def _get_model_name() -> str:
    from smart_travel_buddy.config import settings
    return settings.llm_model
