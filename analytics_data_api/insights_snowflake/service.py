"""Service functions for Snowflake-backed Insights endpoints."""

from analytics_data_api.insights_snowflake.mappers.activity import map_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.queries.activity import get_course_activity_weekly_rows


def get_course_activity_weekly(course_id, start_date=None, end_date=None):
    """Return course activity in the existing API response shape."""
    rows = get_course_activity_weekly_rows(course_id, start_date=start_date, end_date=end_date)
    return map_course_activity_weekly_rows(rows)
