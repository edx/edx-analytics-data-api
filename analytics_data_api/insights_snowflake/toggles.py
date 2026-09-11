"""Waffle flags for Snowflake-backed Insights endpoints."""

from waffle import flag_is_active

INSIGHTS_SNOWFLAKE_FLAG = 'insights_snowflake_enabled'
COURSE_ACTIVITY_SNOWFLAKE_FLAG = 'insights_snowflake_course_activity'
ENROLLMENT_SNOWFLAKE_FLAG = 'insights_snowflake_enrollment_enabled'
COURSE_SUMMARIES_SNOWFLAKE_FLAG = 'insights_snowflake_course_summaries_enabled'
ENGAGEMENT_SNOWFLAKE_FLAG = 'insights_snowflake_engagement_enabled'
PERFORMANCE_SNOWFLAKE_FLAG = 'insights_snowflake_performance_enabled'


def is_insights_snowflake_enabled(request):
    """Return whether Snowflake-backed Insights endpoints are enabled globally."""
    return flag_is_active(request, INSIGHTS_SNOWFLAKE_FLAG)


def is_insights_snowflake_group_enabled(request, group_flag):
    """Return whether the global switch and a specific group switch are active."""
    return is_insights_snowflake_enabled(request) and flag_is_active(request, group_flag)


def is_enrollment_snowflake_enabled(request):
    """Return whether enrollment endpoints should read from Snowflake."""
    return is_insights_snowflake_group_enabled(request, ENROLLMENT_SNOWFLAKE_FLAG)


def is_course_summaries_snowflake_enabled(request):
    """Return whether course summary endpoints should read from Snowflake."""
    return is_insights_snowflake_group_enabled(request, COURSE_SUMMARIES_SNOWFLAKE_FLAG)


def is_engagement_snowflake_enabled(request):
    """Return whether engagement endpoints should read from Snowflake."""
    return is_insights_snowflake_group_enabled(request, ENGAGEMENT_SNOWFLAKE_FLAG)


def is_performance_snowflake_enabled(request):
    """Return whether performance endpoints should read from Snowflake."""
    return is_insights_snowflake_group_enabled(request, PERFORMANCE_SNOWFLAKE_FLAG)


def is_course_activity_snowflake_enabled(request):
    """Return whether course activity should be read from Snowflake."""
    return is_insights_snowflake_enabled(request) and (
        flag_is_active(request, COURSE_ACTIVITY_SNOWFLAKE_FLAG) or
        flag_is_active(request, ENGAGEMENT_SNOWFLAKE_FLAG)
    )
