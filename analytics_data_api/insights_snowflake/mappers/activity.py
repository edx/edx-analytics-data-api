"""Map Snowflake course activity rows into the existing API response shape."""

from itertools import groupby

from analytics_data_api.insights_snowflake.course_ids import get_response_course_id

ACTIVITY_FIELD_MAP = {
    'active': 'any',
    'attempted_problem': 'attempted_problem',
    'played_video': 'played_video',
    'posted_forum': 'posted_forum',
}


def _row_value(row, name):
    """Return a row value from dictionary rows produced by the Snowflake client."""
    if name in row:
        return row[name]
    return row[name.upper()]


def _activity_field(activity_label):
    """Return the API response field name for a Snowflake activity label."""
    activity_label = activity_label.lower()
    return ACTIVITY_FIELD_MAP.get(activity_label, activity_label)


def _course_id(row):
    """Return the canonical course ID from a Snowflake row."""
    return get_response_course_id(_row_value(row, 'course_id'))


def map_course_activity_weekly_rows(rows):
    """Pivot Snowflake course activity rows into existing API response dictionaries."""
    rows = sorted(
        rows or [],
        key=lambda row: (
            _course_id(row) or '',
            _row_value(row, 'interval_start'),
            _row_value(row, 'interval_end'),
        )
    )
    formatted_data = []

    for key, group in groupby(
            rows,
            lambda row: (
                _course_id(row),
                _row_value(row, 'interval_start'),
                _row_value(row, 'interval_end'),
            )
    ):
        item = {
            'course_id': key[0],
            'interval_start': key[1],
            'interval_end': key[2],
            'created': None,
        }

        for row in group:
            activity_field = _activity_field(_row_value(row, 'activity_label'))
            item[activity_field] = int(_row_value(row, 'activity_count'))
            created = _row_value(row, 'created')
            item['created'] = max(created, item['created']) if item['created'] else created

        formatted_data.append(item)

    return formatted_data
