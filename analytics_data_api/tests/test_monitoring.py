"""Tests for Insights-specific Datadog telemetry helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from analytics_data_api import monitoring
from analytics_data_api.insights_snowflake.response_headers import InsightsDataSourceResponseMixin


class MonitoringTests(SimpleTestCase):
    """Verify monitoring helpers remain safe and emit low-cardinality metadata."""

    def test_get_endpoint_group(self):
        self.assertEqual(monitoring.get_endpoint_group('/api/v1/courses/course/enrollment/'), 'enrollment')
        self.assertEqual(monitoring.get_endpoint_group('/api/v1/course_summaries/'), 'course_summaries')
        self.assertEqual(monitoring.get_endpoint_group('/health/'), 'other')

    @patch('analytics_data_api.monitoring.tracer')
    def test_set_current_span_tags(self, mock_tracer):
        span = MagicMock()
        mock_tracer.current_span.return_value = span

        monitoring.set_current_span_tags(
            **{
                'insights.data_source': 'snowflake',
                'insights.endpoint_group': 'enrollment',
            }
        )

        self.assertEqual(span.set_tag.call_count, 2)
        span.set_tag.assert_any_call('insights.data_source', 'snowflake')
        span.set_tag.assert_any_call('insights.endpoint_group', 'enrollment')

    @patch('analytics_data_api.monitoring.tracer')
    def test_trace_snowflake_query(self, mock_tracer):
        span = MagicMock()
        trace_context = MagicMock()
        trace_context.__enter__.return_value = span
        mock_tracer.trace.return_value = trace_context

        with monitoring.trace_snowflake_query('COURSE_ACTIVITY_WEEKLY'):
            pass

        mock_tracer.trace.assert_called_once_with('insights.snowflake.query', span_type='db')
        span.set_tag.assert_any_call('db.system', 'snowflake')
        span.set_tag.assert_any_call('db.operation', 'select')
        span.set_tag.assert_any_call('insights.snowflake.table', 'COURSE_ACTIVITY_WEEKLY')

    @patch('analytics_data_api.monitoring.tracer')
    def test_trace_cache_operation(self, mock_tracer):
        span = MagicMock()
        trace_context = MagicMock()
        trace_context.__enter__.return_value = span
        mock_tracer.trace.return_value = trace_context

        with monitoring.trace_cache_operation('enterprise_users') as active_span:
            active_span.set_tag('insights.cache.result', 'hit')

        mock_tracer.trace.assert_called_once_with('insights.cache', span_type='cache')
        span.set_tag.assert_any_call('insights.cache.name', 'enterprise_users')
        span.set_tag.assert_any_call('insights.cache.result', 'hit')

    @patch('analytics_data_api.insights_snowflake.response_headers.set_current_span_tags')
    def test_data_source_tags_do_not_require_bound_request(self, mock_set_tags):
        view = InsightsDataSourceResponseMixin()
        view.set_insights_data_source_snowflake()

        mock_set_tags.assert_called_once_with(
            **{
                'insights.data_source': 'snowflake',
                'insights.endpoint_group': 'other',
            }
        )

    @patch('analytics_data_api.insights_snowflake.response_headers.set_current_span_tags')
    def test_data_source_tags_include_endpoint_group(self, mock_set_tags):
        view = InsightsDataSourceResponseMixin()
        view.request = SimpleNamespace(path='/api/v1/courses/course/enrollment/')
        view.set_insights_data_source_aurora()

        mock_set_tags.assert_called_once_with(
            **{
                'insights.data_source': 'aurora',
                'insights.endpoint_group': 'enrollment',
            }
        )
