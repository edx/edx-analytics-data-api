"""Snowflake queries for course summary metadata."""

import datetime

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name

COURSE_META_SUMMARY_ENROLLMENT_TABLE = 'COURSE_META_SUMMARY_ENROLLMENT'
COURSE_PROGRAM_METADATA_TABLE = 'COURSE_PROGRAM_METADATA'
COURSE_ENROLLMENT_DAILY_TABLE = 'COURSE_ENROLLMENT_DAILY'


def _date_value(value):
    """Return a date value for date-filtered Snowflake course summary queries."""
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


def _in_filter(column_name, param_prefix, values, prefix='WHERE'):
    """Return a parameterized Snowflake IN filter for controlled columns."""
    if not values:
        return '', {}

    params = {}
    placeholders = []
    for index, value in enumerate(values):
        param_name = '{}_{}'.format(param_prefix, index)
        params[param_name] = value
        placeholders.append('%({})s'.format(param_name))

    return '{} {} IN ({})'.format(prefix, column_name, ', '.join(placeholders)), params


def get_course_summary_rows(course_ids=None):
    """Return Snowflake rows for course summary enrollment metadata."""
    table_name = get_qualified_table_name(COURSE_META_SUMMARY_ENROLLMENT_TABLE)
    where_clause, params = _in_filter('course_id', 'course_id', course_ids)
    sql = """
SELECT
    course_id,
    catalog_course_title,
    catalog_course,
    start_time,
    end_time,
    pacing_type,
    availability,
    enrollment_mode,
    "COUNT" AS count,
    cumulative_count,
    count_change_7_days,
    passing_users,
    created
FROM {table_name}
{where_clause}
ORDER BY course_id, enrollment_mode
""".format(table_name=table_name, where_clause=where_clause)

    return fetch_all(sql, params)


def get_course_summary_program_rows(course_ids=None):
    """Return Snowflake program metadata rows for course summaries."""
    table_name = get_qualified_table_name(COURSE_PROGRAM_METADATA_TABLE)
    where_clause, params = _in_filter('course_id', 'course_id', course_ids)
    sql = """
SELECT
    course_id,
    program_id,
    program_type,
    program_title,
    created
FROM {table_name}
{where_clause}
ORDER BY course_id, program_id
""".format(table_name=table_name, where_clause=where_clause)

    return fetch_all(sql, params)


def get_course_recent_enrollment_rows(course_ids=None, recent_date=None):
    """Return Snowflake course enrollment rows for the requested recent date."""
    table_name = get_qualified_table_name(COURSE_ENROLLMENT_DAILY_TABLE)
    course_filter, course_params = _in_filter('course_id', 'course_id', course_ids, prefix='AND')
    params = {
        'recent_date': _date_value(recent_date),
    }
    params.update(course_params)
    sql = """
SELECT
    course_id,
    "DATE" AS date,
    "COUNT" AS count,
    created
FROM {table_name}
WHERE "DATE" = %(recent_date)s
{course_filter}
ORDER BY course_id
""".format(table_name=table_name, course_filter=course_filter)

    return fetch_all(sql, params)
