"""Tests for Insights-specific Datadog telemetry helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from analytics_data_api import monitoring
from analytics_data_api.insights_snowflake.response_headers import InsightsDataSourceResponseMixin


class MonitoringTests(SimpleTestCase):
    """Verify monitoring helpers remain safe and emit low-cardinality metadata."""

    def test_get_endpoint_group(self):
        enrollment_request = SimpleNamespace(
            resolver_match=SimpleNamespace(url_name='enrollment_latest'),
        )
        summary_request = SimpleNamespace(
            resolver_match=SimpleNamespace(url_name='course_summaries'),
        )
        health_request = SimpleNamespace(
            resolver_match=SimpleNamespace(url_name='health'),
        )

        self.assertEqual(monitoring.get_endpoint_group(enrollment_request), 'enrollment')
        self.assertEqual(monitoring.get_endpoint_group(summary_request), 'course_summaries')
        self.assertEqual(monitoring.get_endpoint_group(health_request), 'other')

    @patch('analytics_data_api.monitoring.tracer')
    def test_set_current_span_tags(self, mock_tracer):
        span = MagicMock()
        mock_tracer.current_root_span.return_value = span

        monitoring.set_current_span_tags(
            **{
                'insights.data_source': 'snowflake',
                'insights.endpoint_group': 'enrollment',
            }
        )

        mock_tracer.current_root_span.assert_called_once_with()
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

        mock_tracer.trace.assert_called_once_with(
            'insights.snowflake.query',
            resource='COURSE_ACTIVITY_WEEKLY',
            span_type='db',
        )
        span.set_tag.assert_any_call('db.system', 'snowflake')
        span.set_tag.assert_any_call('db.operation', 'select')
        span.set_tag.assert_any_call('span.kind', 'client')
        span.set_tag.assert_any_call('insights.snowflake.table', 'COURSE_ACTIVITY_WEEKLY')

    @patch('analytics_data_api.monitoring.tracer')
    def test_trace_snowflake_connection(self, mock_tracer):
        span = MagicMock()
        trace_context = MagicMock()
        trace_context.__enter__.return_value = span
        mock_tracer.trace.return_value = trace_context

        with monitoring.trace_snowflake_connection('COURSE_ACTIVITY_WEEKLY'):
            pass

        mock_tracer.trace.assert_called_once_with('insights.snowflake.connect', span_type='db')
        span.set_tag.assert_any_call('db.system', 'snowflake')
        span.set_tag.assert_any_call('span.kind', 'client')

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
        view.request = SimpleNamespace(
            resolver_match=SimpleNamespace(url_name='enrollment_latest'),
        )
        view.set_insights_data_source_aurora()

        mock_set_tags.assert_called_once_with(
            **{
                'insights.data_source': 'aurora',
                'insights.endpoint_group': 'enrollment',
            }
        )
