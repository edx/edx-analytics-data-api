"""Response header helpers for Snowflake-backed Insights endpoints."""

from analytics_data_api.monitoring import get_endpoint_group, set_current_span_tags

DATA_SOURCE_HEADER = 'X-Insights-Data-Source'
DATA_SOURCE_AURORA = 'aurora'
DATA_SOURCE_SNOWFLAKE = 'snowflake'


class InsightsDataSourceResponseMixin:
    """Add the Insights data source response header when a view sets one."""

    data_source_header = DATA_SOURCE_HEADER
    data_source_aurora = DATA_SOURCE_AURORA
    data_source_snowflake = DATA_SOURCE_SNOWFLAKE
    insights_data_source = None

    def _set_data_source_span_tags(self, data_source):
        """Tag the active request span without requiring a bound test request."""
        request = getattr(self, 'request', None)
        path = getattr(request, 'path', '')
        set_current_span_tags(
            **{
                'insights.data_source': data_source,
                'insights.endpoint_group': get_endpoint_group(path),
            }
        )

    def set_insights_data_source_aurora(self):
        """Mark the current response as using Aurora."""
        self.insights_data_source = self.data_source_aurora
        self._set_data_source_span_tags(self.data_source_aurora)

    def set_insights_data_source_snowflake(self):
        """Mark the current response as using Snowflake."""
        self.insights_data_source = self.data_source_snowflake
        self._set_data_source_span_tags(self.data_source_snowflake)

    def finalize_response(self, request, response, *args, **kwargs):
        path = getattr(request, 'path', '')
        if not isinstance(path, str):
            path = ''
        set_current_span_tags(
            **{
                'insights.api_version': 'v1' if '/api/v1/' in path else 'v0',
                'insights.endpoint_group': get_endpoint_group(path),
            }
        )
        response = super().finalize_response(request, response, *args, **kwargs)
        if self.insights_data_source:
            response[self.data_source_header] = self.insights_data_source
        return response
