"""Response header helpers for Snowflake-backed Insights endpoints."""

DATA_SOURCE_HEADER = 'X-Insights-Data-Source'
DATA_SOURCE_AURORA = 'aurora'
DATA_SOURCE_SNOWFLAKE = 'snowflake'


class InsightsDataSourceResponseMixin:
    """Add the Insights data source response header when a view sets one."""

    data_source_header = DATA_SOURCE_HEADER
    data_source_aurora = DATA_SOURCE_AURORA
    data_source_snowflake = DATA_SOURCE_SNOWFLAKE
    insights_data_source = None

    def set_insights_data_source_aurora(self):
        """Mark the current response as using Aurora."""
        self.insights_data_source = self.data_source_aurora

    def set_insights_data_source_snowflake(self):
        """Mark the current response as using Snowflake."""
        self.insights_data_source = self.data_source_snowflake

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if self.insights_data_source:
            response[self.data_source_header] = self.insights_data_source
        return response
