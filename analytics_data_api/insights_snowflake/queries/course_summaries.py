"""Snowflake queries for course summary metadata."""

import datetime

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name
from analytics_data_api.insights_snowflake.course_ids import (
    build_preferred_course_id_filter,
    build_unfiltered_course_id_filter,
)

COURSE_META_SUMMARY_ENROLLMENT_TABLE = 'COURSE_META_SUMMARY_ENROLLMENT'
COURSE_PROGRAM_METADATA_TABLE = 'COURSE_PROGRAM_METADATA'
COURSE_ENROLLMENT_DAILY_TABLE = 'COURSE_ENROLLMENT_DAILY'
COURSE_ENROLLMENT_MODE_DAILY_TABLE = 'COURSE_ENROLLMENT_MODE_DAILY'


def _date_value(value):
    """Return a date value for date-filtered Snowflake course summary queries."""
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


def get_course_summary_rows(course_ids=None):
    """Return Snowflake rows for course summary enrollment metadata."""
    table_name = get_qualified_table_name(COURSE_META_SUMMARY_ENROLLMENT_TABLE)
    if course_ids:
        where_clause, params = build_preferred_course_id_filter(
            table_name,
            'course_id',
            course_ids,
            alias='source',
            scope_columns=('enrollment_mode',),
        )
    else:
        where_clause, params = build_unfiltered_course_id_filter(
            table_name,
            'course_id',
            alias='source',
            scope_columns=('enrollment_mode',),
        )
    from_clause = '{} AS source'.format(table_name)
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
FROM {from_clause}
{where_clause}
ORDER BY course_id, enrollment_mode
""".format(from_clause=from_clause, where_clause=where_clause)

    return fetch_all(sql, params, table_name=COURSE_META_SUMMARY_ENROLLMENT_TABLE)


def get_course_summary_program_rows(course_ids=None):
    """Return Snowflake program metadata rows for course summaries."""
    table_name = get_qualified_table_name(COURSE_PROGRAM_METADATA_TABLE)
    if course_ids:
        where_clause, params = build_preferred_course_id_filter(
            table_name,
            'course_id',
            course_ids,
            alias='source',
            scope_columns=('program_id',),
        )
    else:
        where_clause, params = build_unfiltered_course_id_filter(
            table_name,
            'course_id',
            alias='source',
            scope_columns=('program_id',),
        )
    from_clause = '{} AS source'.format(table_name)
    sql = """
SELECT
    course_id,
    program_id,
    program_type,
    program_title,
    created
FROM {from_clause}
{where_clause}
ORDER BY course_id, program_id
""".format(from_clause=from_clause, where_clause=where_clause)

    return fetch_all(sql, params, table_name=COURSE_PROGRAM_METADATA_TABLE)


def get_course_recent_enrollment_rows(course_ids=None, recent_date=None):
    """Return Snowflake course enrollment rows for the requested recent date."""
    table_name = get_qualified_table_name(COURSE_ENROLLMENT_DAILY_TABLE)
    if course_ids:
        course_filter, course_params = build_preferred_course_id_filter(
            table_name,
            'course_id',
            course_ids,
            alias='source',
            prefix='AND',
            scope_columns=('"DATE"',),
        )
    else:
        course_filter, course_params = build_unfiltered_course_id_filter(
            table_name,
            'course_id',
            alias='source',
            prefix='AND',
            scope_columns=('"DATE"',),
        )
    from_clause = '{} AS source'.format(table_name)
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
FROM {from_clause}
WHERE "DATE" = %(recent_date)s
{course_filter}
ORDER BY course_id
""".format(from_clause=from_clause, course_filter=course_filter)

    return fetch_all(sql, params, table_name=COURSE_ENROLLMENT_DAILY_TABLE)


def get_course_enrollment_latest_date():
    """Return the latest date of the daily enrollment counts, or None when there are none.

    The data lags the calendar by a day or two, so date ranges end on this date.
    """
    table_name = get_qualified_table_name(COURSE_ENROLLMENT_DAILY_TABLE)
    sql = """
SELECT
    MAX("DATE") AS latest_date
FROM {table_name}
""".format(table_name=table_name)

    rows = fetch_all(sql, {}, table_name=COURSE_ENROLLMENT_DAILY_TABLE)
    return _date_value(rows[0]['latest_date']) if rows else None


def _get_enrollment_rows_on_dates(table, columns, scope_columns, course_ids, dates):
    """Return the rows of a daily enrollment table on the given dates, for the requested courses."""
    table_name = get_qualified_table_name(table)
    if course_ids:
        course_filter, course_params = build_preferred_course_id_filter(
            table_name,
            'course_id',
            course_ids,
            alias='source',
            prefix='AND',
            scope_columns=scope_columns,
        )
    else:
        course_filter, course_params = build_unfiltered_course_id_filter(
            table_name,
            'course_id',
            alias='source',
            prefix='AND',
            scope_columns=scope_columns,
        )
    params = {
        'date_{}'.format(index): _date_value(date) for index, date in enumerate(dates)
    }
    date_placeholders = ', '.join('%({})s'.format(name) for name in params)
    params.update(course_params)
    sql = """
SELECT
    {select_columns}
FROM {table_name} AS source
WHERE "DATE" IN ({date_placeholders})
{course_filter}
ORDER BY course_id, date
""".format(
        select_columns=',\n    '.join(columns),
        table_name=table_name,
        date_placeholders=date_placeholders,
        course_filter=course_filter,
    )

    return fetch_all(sql, params, table_name=table)


def get_course_range_enrollment_rows(course_ids=None, dates=()):
    """Return the course enrollment counts (current and cumulative) on the given dates."""
    return _get_enrollment_rows_on_dates(
        COURSE_ENROLLMENT_DAILY_TABLE,
        ['course_id', '"DATE" AS date', '"COUNT" AS count', 'cumulative_count'],
        ('"DATE"',),
        course_ids,
        dates,
    )


def get_course_range_mode_enrollment_rows(course_ids=None, dates=()):
    """Return the enrollment counts (current and cumulative) of each mode on the given dates."""
    return _get_enrollment_rows_on_dates(
        COURSE_ENROLLMENT_MODE_DAILY_TABLE,
        ['course_id', '"DATE" AS date', 'mode', '"COUNT" AS count', 'cumulative_count'],
        ('"DATE"', 'mode'),
        course_ids,
        dates,
    )
