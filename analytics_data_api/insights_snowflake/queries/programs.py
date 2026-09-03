"""Snowflake queries for program metadata."""

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name

COURSE_PROGRAM_METADATA_TABLE = 'COURSE_PROGRAM_METADATA'


def _in_filter(column_name, param_prefix, values):
    """Return a parameterized Snowflake IN filter for controlled columns."""
    if not values:
        return '', {}

    params = {}
    placeholders = []
    for index, value in enumerate(values):
        param_name = '{}_{}'.format(param_prefix, index)
        params[param_name] = value
        placeholders.append('%({})s'.format(param_name))

    return 'WHERE {} IN ({})'.format(column_name, ', '.join(placeholders)), params


def get_program_metadata_rows(program_ids=None):
    """Return Snowflake rows for course program metadata."""
    table_name = get_qualified_table_name(COURSE_PROGRAM_METADATA_TABLE)
    where_clause, params = _in_filter('program_id', 'program_id', program_ids)
    sql = """
SELECT
    program_id,
    program_type,
    program_title,
    course_id,
    created
FROM {table_name}
{where_clause}
ORDER BY program_id, course_id
""".format(table_name=table_name, where_clause=where_clause)

    return fetch_all(sql, params)
