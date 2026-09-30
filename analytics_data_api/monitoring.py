"""Datadog helpers for Insights-specific request telemetry."""

from contextlib import contextmanager

try:
    from ddtrace import tracer
except ImportError:  # pragma: no cover - ddtrace is installed by deployment configuration
    tracer = None


ENDPOINT_GROUPS = (
    ('course_summaries', 'course_summaries'),
    ('programs', 'course_summaries'),
    ('enrollment', 'enrollment'),
    ('activity', 'engagement'),
    ('videos', 'engagement'),
    ('problems', 'performance'),
)


def get_endpoint_group(path):
    """Return the low-cardinality Insights endpoint group for a request path."""
    for path_fragment, endpoint_group in ENDPOINT_GROUPS:
        if path_fragment in path:
            return endpoint_group
    return 'other'


def set_current_span_tags(**tags):
    """Set tags on the active Datadog span when tracing is available."""
    if tracer is None:
        return

    span = tracer.current_span()
    if span is not None:
        for key, value in tags.items():
            if value is not None:
                span.set_tag(key, value)


@contextmanager
def trace_snowflake_query(table_name):
    """Trace one read-only Snowflake query without exposing SQL or parameters."""
    if tracer is None:
        yield None
        return

    with tracer.trace('insights.snowflake.query', span_type='db') as span:
        span.set_tag('db.system', 'snowflake')
        span.set_tag('db.operation', 'select')
        span.set_tag('insights.data_source', 'snowflake')
        span.set_tag('insights.snowflake.table', table_name)
        yield span


@contextmanager
def trace_cache_operation(cache_name):
    """Trace an explicit Insights cache lookup."""
    if tracer is None:
        yield None
        return

    with tracer.trace('insights.cache', span_type='cache') as span:
        span.set_tag('insights.cache.name', cache_name)
        yield span
