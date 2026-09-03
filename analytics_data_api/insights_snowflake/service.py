"""Service functions for Snowflake-backed Insights endpoints."""

from analytics_data_api.insights_snowflake.mappers.activity import map_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.mappers.course_summaries import map_course_summary_rows
from analytics_data_api.insights_snowflake.mappers.enrollment import (
    map_course_enrollment_daily_rows,
    map_course_enrollment_education_rows,
    map_course_enrollment_gender_rows,
    map_course_enrollment_location_rows,
    map_course_enrollment_mode_rows,
)
from analytics_data_api.insights_snowflake.mappers.programs import map_program_metadata_rows
from analytics_data_api.insights_snowflake.mappers.videos import map_course_video_rows, map_video_timeline_rows
from analytics_data_api.insights_snowflake.queries.activity import get_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.queries.course_summaries import (
    get_course_recent_enrollment_rows,
    get_course_summary_program_rows,
    get_course_summary_rows,
)
from analytics_data_api.insights_snowflake.queries.enrollment import (
    get_course_enrollment_daily_rows,
    get_course_enrollment_education_rows,
    get_course_enrollment_gender_rows,
    get_course_enrollment_location_rows,
    get_course_enrollment_mode_rows,
)
from analytics_data_api.insights_snowflake.queries.programs import get_program_metadata_rows
from analytics_data_api.insights_snowflake.queries.videos import get_course_video_rows, get_video_timeline_rows


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


def get_program_metadata(program_ids=None):
    """Return program metadata in the existing API response shape."""
    rows = get_program_metadata_rows(program_ids=program_ids)
    return map_program_metadata_rows(rows)


def get_course_summaries(course_ids=None, include_programs=False, recent_date=None, exclude=None):
    """Return course summaries in the existing API response shape."""
    summary_rows = get_course_summary_rows(course_ids=course_ids)
    program_rows = get_course_summary_program_rows(course_ids=course_ids) if include_programs else None
    recent_rows = get_course_recent_enrollment_rows(
        course_ids=course_ids,
        recent_date=recent_date,
    ) if recent_date else None

    return map_course_summary_rows(
        summary_rows,
        program_rows=program_rows,
        recent_rows=recent_rows,
        exclude=exclude,
    )


def get_course_videos(course_id):
    """Return course videos in the existing API response shape."""
    rows = get_course_video_rows(course_id)
    return map_course_video_rows(rows)


def get_video_timeline(video_id):
    """Return video timeline metrics in the existing API response shape."""
    rows = get_video_timeline_rows(video_id)
    return map_video_timeline_rows(rows)
