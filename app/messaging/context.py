from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind

from app.core.correlation import HEADER, bind_correlation_id, correlation_id

tracer = trace.get_tracer("sirius_food.messaging")


def outgoing_headers() -> dict[str, str]:
    headers = {HEADER: correlation_id.get()} if correlation_id.get() else {}
    propagate.inject(headers)
    return headers


@contextmanager
def continue_trace(headers: dict | None, span_name: str, kind: SpanKind = SpanKind.CONSUMER) -> Iterator[None]:
    headers = {key: value.decode() if isinstance(value, bytes) else str(value) for key, value in (headers or {}).items()}
    bind_correlation_id(headers.get(HEADER))
    with tracer.start_as_current_span(span_name, context=propagate.extract(headers), kind=kind):
        yield
