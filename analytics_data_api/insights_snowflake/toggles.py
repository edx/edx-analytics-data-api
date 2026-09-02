"""Waffle flags for Snowflake-backed Insights endpoints."""

from waffle import flag_is_active

INSIGHTS_SNOWFLAKE_FLAG = 'insights_snowflake_enabled'
COURSE_ACTIVITY_SNOWFLAKE_FLAG = 'insights_snowflake_course_activity'


def is_insights_snowflake_enabled(request):
    """Return whether Snowflake-backed Insights endpoints are enabled globally."""
    return flag_is_active(request, INSIGHTS_SNOWFLAKE_FLAG)


def is_course_activity_snowflake_enabled(request):
    """Return whether course activity should be read from Snowflake."""
    return (
        is_insights_snowflake_enabled(request) or
        flag_is_active(request, COURSE_ACTIVITY_SNOWFLAKE_FLAG)
    )
