"""Map Snowflake video rows into the existing API response shape."""

COURSE_VIDEO_FIELDS = (
    'pipeline_video_id',
    'encoded_module_id',
    'duration',
    'segment_length',
    'users_at_start',
    'users_at_end',
    'created',
)
VIDEO_TIMELINE_FIELDS = (
    'segment',
    'num_users',
    'num_views',
    'created',
)
INTEGER_FIELDS = (
    'duration',
    'segment_length',
    'users_at_start',
    'users_at_end',
    'segment',
    'num_users',
    'num_views',
)


def _row_value(row, name):
    """Return a row value from dictionary rows produced by the Snowflake client."""
    if name in row:
        return row[name]
    return row[name.upper()]


def _api_value(row, name):
    """Return the API-compatible value for a Snowflake row field."""
    value = _row_value(row, name)
    if name in INTEGER_FIELDS:
        return int(value)
    return value


def _map_rows(rows, fields):
    """Map Snowflake rows to dictionaries containing only API response fields."""
    return [
        {
            field: _api_value(row, field)
            for field in fields
        }
        for row in rows or []
    ]


def map_course_video_rows(rows):
    """Map Snowflake course video rows into existing API response dictionaries."""
    return _map_rows(rows, COURSE_VIDEO_FIELDS)


def map_video_timeline_rows(rows):
    """Map Snowflake video timeline rows into existing API response dictionaries."""
    return _map_rows(rows, VIDEO_TIMELINE_FIELDS)
