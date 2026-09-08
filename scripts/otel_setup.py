"""OpenTelemetry SDK for the Guardrails server process only.

Libraries emit spans through the API. This module configures the TracerProvider,
OTLP export, sampling, W3C propagation, optional HTTP instrumentation, and flush
on shutdown.
"""

from __future__ import annotations

import atexit
import logging
import os
from typing import Any
from urllib.parse import urlparse

log = logging.getLogger("guardrails.otel")

_provider: Any = None


def _disabled() -> bool:
    return os.environ.get("OTEL_SDK_DISABLED", "").lower() in {"1", "true", "yes"}


def _resource():
    from opentelemetry.sdk.resources import Resource

    attributes = {
        "service.name": os.environ.get("OTEL_SERVICE_NAME", "nemo-guardrails"),
        "service.namespace": os.environ.get("OTEL_SERVICE_NAMESPACE", "guardrails"),
        "deployment.environment": os.environ.get("DEPLOYMENT_ENVIRONMENT", "local"),
    }
    extra = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
    for pair in extra.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            key, value = key.strip(), value.strip()
            if key:
                attributes[key] = value
    return Resource.create(attributes)


def _sampler():
    from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased, TraceIdRatioBased

    name = os.environ.get("OTEL_TRACES_SAMPLER", "parentbased_traceidratio").lower()
    if name in {"always_on", "alwayson"}:
        return ALWAYS_ON
    ratio = float(os.environ.get("OTEL_TRACES_SAMPLER_ARG", "1"))
    ratio = min(max(ratio, 0.0), 1.0)
    return ParentBased(root=TraceIdRatioBased(ratio))


def _otlp_exporter():
    protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").strip().lower()
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

    if protocol in {"http/protobuf", "http", "http/json"}:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        traces_url = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", endpoint.rstrip("/"))
        if not traces_url.endswith("/v1/traces"):
            traces_url = f"{traces_url}/v1/traces"
        log.info("OTLP HTTP exporter -> %s", traces_url)
        return OTLPSpanExporter(endpoint=traces_url)

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    grpc_target = parsed.netloc or parsed.path
    insecure = parsed.scheme != "https"
    log.info("OTLP gRPC exporter -> %s (insecure=%s)", grpc_target, insecure)
    return OTLPSpanExporter(endpoint=grpc_target, insecure=insecure)


def _instrument_libraries() -> None:
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        log.info("httpx instrumentation enabled")
    except Exception as exc:
        log.info("httpx instrumentation skipped: %s", exc)


def _install_shutdown(provider) -> None:
    def _flush_and_shutdown() -> None:
        try:
            provider.force_flush(timeout_millis=10_000)
        except Exception:
            log.exception("OpenTelemetry force_flush failed")
        try:
            provider.shutdown()
        except Exception:
            log.exception("OpenTelemetry shutdown failed")

    atexit.register(_flush_and_shutdown)


def setup_otel() -> None:
    global _provider
    if _disabled():
        log.info("OTEL_SDK_DISABLED is set; skipping SDK setup")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.propagators.composite import CompositePropagator
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
        from opentelemetry.baggage.propagation import W3CBaggagePropagator
    except ImportError as exc:
        log.warning(
            "OpenTelemetry SDK ausente (%s). Instale na imagem: "
            "pip install opentelemetry-sdk opentelemetry-exporter-otlp",
            exc,
        )
        return

    try:
        exporter = _otlp_exporter()
    except ImportError as exc:
        log.warning("OTLP exporter ausente (%s). Instale opentelemetry-exporter-otlp", exc)
        return

    provider = TracerProvider(resource=_resource(), sampler=_sampler())
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
            export_timeout_millis=10_000,
        )
    )
    trace.set_tracer_provider(provider)
    set_global_textmap(
        CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()])
    )
    _provider = provider
    _install_shutdown(provider)
    _instrument_libraries()
    log.info(
        "OpenTelemetry ready service=%s env=%s sampler_arg=%s",
        os.environ.get("OTEL_SERVICE_NAME", "nemo-guardrails"),
        os.environ.get("DEPLOYMENT_ENVIRONMENT", "local"),
        os.environ.get("OTEL_TRACES_SAMPLER_ARG", "1"),
    )


def instrument_fastapi_app(app) -> None:
    if _disabled():
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        log.info("FastAPI app instrumentation enabled")
    except Exception as exc:
        log.info("FastAPI app instrumentation skipped: %s", exc)
