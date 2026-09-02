"""Service functions for Snowflake-backed Insights endpoints."""

from analytics_data_api.insights_snowflake.mappers.activity import map_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.mappers.enrollment import (
    map_course_enrollment_daily_rows,
    map_course_enrollment_education_rows,
    map_course_enrollment_gender_rows,
    map_course_enrollment_location_rows,
    map_course_enrollment_mode_rows,
)
from analytics_data_api.insights_snowflake.queries.activity import get_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.queries.enrollment import (
    get_course_enrollment_daily_rows,
    get_course_enrollment_education_rows,
    get_course_enrollment_gender_rows,
    get_course_enrollment_location_rows,
    get_course_enrollment_mode_rows,
)


def get_course_activity_weekly(course_id, start_date=None, end_date=None):
    """Return course activity in the existing API response shape."""
    rows = get_course_activity_weekly_rows(course_id, start_date=start_date, end_date=end_date)
    return map_course_activity_weekly_rows(rows)


def get_course_enrollment(course_id, start_date=None, end_date=None):
    """Return course enrollment counts in the existing API response shape."""
    rows = get_course_enrollment_daily_rows(course_id, start_date=start_date, end_date=end_date)
    return map_course_enrollment_daily_rows(rows)


def get_course_enrollment_mode(course_id, start_date=None, end_date=None):
    """Return course enrollment mode counts in the existing API response shape."""
    rows = get_course_enrollment_mode_rows(course_id, start_date=start_date, end_date=end_date)
    return map_course_enrollment_mode_rows(rows)


def get_course_enrollment_education(course_id, start_date=None, end_date=None):
    """Return course enrollment education counts in the existing API response shape."""
    rows = get_course_enrollment_education_rows(course_id, start_date=start_date, end_date=end_date)
    return map_course_enrollment_education_rows(rows)


def get_course_enrollment_gender(course_id, start_date=None, end_date=None):
    """Return course enrollment gender counts in the existing API response shape."""
    rows = get_course_enrollment_gender_rows(course_id, start_date=start_date, end_date=end_date)
    return map_course_enrollment_gender_rows(rows)


def get_course_enrollment_location(course_id, start_date=None, end_date=None):
    """Return course enrollment location counts in the existing API response shape."""
    rows = get_course_enrollment_location_rows(course_id, start_date=start_date, end_date=end_date)
    return map_course_enrollment_location_rows(rows)
