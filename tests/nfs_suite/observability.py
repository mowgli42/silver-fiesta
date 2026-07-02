"""
OpenTelemetry instrumentation for SignOz / OTLP collectors.

Enable with OTEL_ENABLED=true and OTEL_EXPORTER_OTLP_ENDPOINT.
"""
from __future__ import annotations

import logging
import os
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional

_RUN_ID: Optional[str] = None
_TRACER = None
_CONFIGURED = False

logger = logging.getLogger("nfs_suite")


def get_run_id() -> str:
    global _RUN_ID
    if _RUN_ID is None:
        _RUN_ID = os.environ.get("NFS_RUN_ID") or str(uuid.uuid4())
        os.environ["NFS_RUN_ID"] = _RUN_ID
    return _RUN_ID


def is_enabled() -> bool:
    return os.environ.get("OTEL_ENABLED", "").lower() in ("1", "true", "yes")


def configure_observability(
    service_name: str = "nfs-test-runner",
    extra_attributes: Optional[Dict[str, Any]] = None,
) -> bool:
    """Initialize OTLP logging/tracing. Returns True if configured."""
    global _TRACER, _CONFIGURED

    if _CONFIGURED:
        return _TRACER is not None

    _CONFIGURED = True
    if not is_enabled():
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("OpenTelemetry packages not installed; observability disabled")
        return False

    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"
    )
    attrs = {
        "service.name": service_name,
        "nfs.run_id": get_run_id(),
        "nfs.server": os.environ.get("NFS_SERVER", ""),
        "nfs.server_type": os.environ.get("NFS_SERVER_TYPE", ""),
        "nfs.fault_profile": os.environ.get("FAULT_PROFILE", "none"),
    }
    if extra_attributes:
        attrs.update(extra_attributes)

    resource = Resource.create(attrs)
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _TRACER = trace.get_tracer("nfs_suite")
    return True


def get_tracer():
    configure_observability()
    return _TRACER


@contextmanager
def span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager for a trace span (no-op if OTEL disabled)."""
    tracer = get_tracer()
    if tracer is None:
        yield
        return
    with tracer.start_as_current_span(name) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, str(v))
        yield


def log_structured(level: str, message: str, **fields: Any) -> None:
    """Emit a structured log line (always) and span event (if OTEL on)."""
    run_id = get_run_id()
    payload = {"run_id": run_id, "message": message, **fields}
    line = " ".join(f"{k}={v!r}" for k, v in payload.items())
    getattr(logger, level.lower(), logger.info)(line)

    tracer = get_tracer()
    if tracer is not None:
        with tracer.start_as_current_span("log") as s:
            s.set_attribute("log.message", message)
            for k, v in fields.items():
                s.set_attribute(f"log.{k}", str(v))
