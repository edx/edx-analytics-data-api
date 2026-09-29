"""Snowflake queries for course enrollment metrics."""

import datetime

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name
from analytics_data_api.insights_snowflake.course_ids import build_preferred_course_id_filter

COURSE_ENROLLMENT_DAILY_TABLE = 'COURSE_ENROLLMENT_DAILY'
COURSE_ENROLLMENT_MODE_DAILY_TABLE = 'COURSE_ENROLLMENT_MODE_DAILY'
COURSE_ENROLLMENT_EDUCATION_LEVEL_CURRENT_TABLE = 'COURSE_ENROLLMENT_EDUCATION_LEVEL_CURRENT'
COURSE_ENROLLMENT_GENDER_DAILY_TABLE = 'COURSE_ENROLLMENT_GENDER_DAILY'
COURSE_ENROLLMENT_LOCATION_CURRENT_TABLE = 'COURSE_ENROLLMENT_LOCATION_CURRENT'


def _date_value(value):
    """Return a date value for date-filtered Snowflake enrollment queries."""
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


def _get_course_enrollment_rows(
    table,
    columns,
    order_by,
    scope_columns,
    course_id,
    start_date=None,
    end_date=None,
):
    """Return Snowflake enrollment rows for one controlled table."""
    table_name = get_qualified_table_name(table)
    select_columns = ',\n    '.join(columns)
    course_filter, params = build_preferred_course_id_filter(
        table_name,
        'course_id',
        [course_id],
        alias='source',
        prefix='',
        scope_columns=scope_columns,
    )

    if start_date or end_date:
        params.update({
            'start_date': _date_value(start_date),
            'end_date': _date_value(end_date),
        })
        sql = """
SELECT
    {select_columns}
FROM {table_name} AS source
WHERE {course_filter}
  AND (%(start_date)s IS NULL OR "DATE" >= %(start_date)s)
  AND (%(end_date)s IS NULL OR "DATE" < %(end_date)s)
ORDER BY {order_by}
""".format(
            select_columns=select_columns,
            table_name=table_name,
            course_filter=course_filter,
            order_by=order_by,
        )
    else:
        latest_course_filter, _ = build_preferred_course_id_filter(
            table_name,
            'course_id',
            [course_id],
            alias='latest',
            prefix='',
            scope_columns=scope_columns,
        )
        sql = """
SELECT
    {select_columns}
FROM {table_name} AS source
WHERE {course_filter}
  AND "DATE" = (
      SELECT MAX("DATE")
      FROM {table_name} AS latest
      WHERE {latest_course_filter}
  )
ORDER BY {order_by}
""".format(
            select_columns=select_columns,
            table_name=table_name,
            course_filter=course_filter,
            latest_course_filter=latest_course_filter,
            order_by=order_by,
        )

    return fetch_all(sql, params)


def get_course_enrollment_daily_rows(course_id, start_date=None, end_date=None):
    """Return Snowflake rows for course enrollment counts."""
    return _get_course_enrollment_rows(
        COURSE_ENROLLMENT_DAILY_TABLE,
        ['course_id', '"DATE" AS date', '"COUNT" AS count', 'created'],
        'course_id, date',
        ('"DATE"',),
        course_id,
        start_date=start_date,
        end_date=end_date,
    )


def get_course_enrollment_mode_rows(course_id, start_date=None, end_date=None):
    """Return Snowflake rows for enrollment mode counts."""
    return _get_course_enrollment_rows(
        COURSE_ENROLLMENT_MODE_DAILY_TABLE,
        ['course_id', '"DATE" AS date', 'mode', '"COUNT" AS count', 'cumulative_count', 'created'],
        'course_id, date, mode',
        ('"DATE"', 'mode'),
        course_id,
        start_date=start_date,
        end_date=end_date,
    )


def get_course_enrollment_education_rows(course_id, start_date=None, end_date=None):
    """Return Snowflake rows for enrollment education counts."""
    return _get_course_enrollment_rows(
        COURSE_ENROLLMENT_EDUCATION_LEVEL_CURRENT_TABLE,
        ['course_id', '"DATE" AS date', 'education_level', '"COUNT" AS count', 'created'],
        'course_id, date, education_level',
        ('"DATE"', 'education_level'),
        course_id,
        start_date=start_date,
        end_date=end_date,
    )


def get_course_enrollment_gender_rows(course_id, start_date=None, end_date=None):
    """Return Snowflake rows for enrollment gender counts."""
    return _get_course_enrollment_rows(
        COURSE_ENROLLMENT_GENDER_DAILY_TABLE,
        ['course_id', '"DATE" AS date', 'gender', '"COUNT" AS count', 'created'],
        'course_id, date, gender',
        ('"DATE"', 'gender'),
        course_id,
        start_date=start_date,
        end_date=end_date,
    )


def get_course_enrollment_location_rows(course_id, start_date=None, end_date=None):
    """Return Snowflake rows for enrollment location counts."""
    return _get_course_enrollment_rows(
        COURSE_ENROLLMENT_LOCATION_CURRENT_TABLE,
        ['course_id', '"DATE" AS date', 'country_code', '"COUNT" AS count', 'created'],
        'course_id, date, country_code',
        ('"DATE"', 'country_code'),
        course_id,
        start_date=start_date,
        end_date=end_date,
    )
