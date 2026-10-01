"""Datadog helpers for Insights-specific request telemetry."""

from contextlib import contextmanager

try:
    from ddtrace import tracer
except ImportError:  # pragma: no cover - ddtrace is installed by deployment configuration
    tracer = None


ENDPOINT_GROUPS = {
    'course_summaries': 'course_summaries',
    'programs': 'course_summaries',
    'enrollment_latest': 'enrollment',
    'enrollment_by_mode': 'enrollment',
    'enrollment_by_education': 'enrollment',
    'enrollment_by_gender': 'enrollment',
    'enrollment_by_location': 'enrollment',
    'activity': 'engagement',
    'videos': 'engagement',
    'timeline': 'engagement',
    'problems': 'performance',
    'answer_distribution': 'performance',
}


def get_endpoint_group(request):
    """Return a low-cardinality group from Django's resolved route name."""
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = getattr(resolver_match, 'url_name', None)
    return ENDPOINT_GROUPS.get(url_name, 'other')


def set_current_span_tags(**tags):
    """Set tags on the active Datadog span when tracing is available."""
    if tracer is None:
        return

    if hasattr(tracer, 'current_root_span'):
        span = tracer.current_root_span()
    else:
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

    with tracer.trace('insights.snowflake.query', resource=table_name, span_type='db') as span:
        span.set_tag('db.system', 'snowflake')
        span.set_tag('db.operation', 'select')
        span.set_tag('span.kind', 'client')
        span.set_tag('insights.data_source', 'snowflake')
        span.set_tag('insights.snowflake.table', table_name)
        yield span


@contextmanager
def trace_snowflake_connection(table_name):
    """Trace the Snowflake connection setup separately from query execution."""
    if tracer is None:
        yield None
        return

    with tracer.trace('insights.snowflake.connect', span_type='db') as span:
        span.set_tag('db.system', 'snowflake')
        span.set_tag('span.kind', 'client')
        span.set_tag('insights.data_source', 'snowflake')
        span.set_tag('insights.snowflake.table', table_name)
        yield span
