"""Snowflake queries for course activity metrics."""

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name

COURSE_ACTIVITY_WEEKLY_TABLE = 'COURSE_ACTIVITY_WEEKLY'


def get_course_activity_weekly_rows(course_id, start_date=None, end_date=None):
    """Return Snowflake rows for course activity weekly metrics."""
    table_name = get_qualified_table_name(COURSE_ACTIVITY_WEEKLY_TABLE)
    params = {
        'course_id': course_id,
    }

    if start_date or end_date:
        params.update({
            'start_date': start_date,
            'end_date': end_date,
        })
        sql = """
SELECT
    course_id,
    interval_start,
    interval_end,
    label AS activity_label,
    "COUNT" AS activity_count,
    created
FROM {table_name}
WHERE course_id = %(course_id)s
  AND (%(start_date)s IS NULL OR interval_start >= %(start_date)s)
  AND (%(end_date)s IS NULL OR interval_end < %(end_date)s)
ORDER BY course_id, interval_start, interval_end, label
""".format(table_name=table_name)
    else:
        sql = """
SELECT
    course_id,
    interval_start,
    interval_end,
    label AS activity_label,
    "COUNT" AS activity_count,
    created
FROM {table_name}
WHERE course_id = %(course_id)s
  AND interval_end = (
      SELECT MAX(interval_end)
      FROM {table_name}
      WHERE course_id = %(course_id)s
  )
ORDER BY course_id, interval_start, interval_end, label
""".format(table_name=table_name)

    return fetch_all(sql, params)
