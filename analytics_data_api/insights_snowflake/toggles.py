"""Waffle flags for Snowflake-backed Insights endpoints."""

from waffle import flag_is_active

COURSE_ACTIVITY_SNOWFLAKE_FLAG = 'insights_snowflake_course_activity'


def is_course_activity_snowflake_enabled(request):
    """Return whether course activity should be read from Snowflake."""
    return flag_is_active(request, COURSE_ACTIVITY_SNOWFLAKE_FLAG)
