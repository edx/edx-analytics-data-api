"""Snowflake queries for video engagement metrics."""

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name

VIDEO_TABLE = 'VIDEO'
VIDEO_TIMELINE_TABLE = 'VIDEO_TIMELINE'


def get_course_video_rows(course_id):
    """Return Snowflake rows for videos in a course."""
    table_name = get_qualified_table_name(VIDEO_TABLE)
    sql = """
SELECT
    courserun_key AS course_id,
    pipeline_video_id,
    encoded_module_id,
    duration,
    segment_length,
    users_at_start,
    users_at_end,
    created
FROM {table_name}
WHERE courserun_key = %(course_id)s
ORDER BY pipeline_video_id
""".format(table_name=table_name)

    return fetch_all(sql, {'course_id': course_id})


def get_video_timeline_rows(video_id):
    """Return Snowflake rows for a video's timeline."""
    table_name = get_qualified_table_name(VIDEO_TIMELINE_TABLE)
    sql = """
SELECT
    segment,
    num_users,
    num_views,
    created
FROM {table_name}
WHERE pipeline_video_id = %(video_id)s
ORDER BY segment
""".format(table_name=table_name)

    return fetch_all(sql, {'video_id': video_id})
