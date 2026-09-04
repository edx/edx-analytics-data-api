"""Snowflake queries for performance metrics."""

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name

PROBLEM_ANSWER_DISTRIBUTION_TABLE = 'PROBLEM_ANSWER_DISTRIBUTION'


def get_course_problem_rows(course_id):
    """Return Snowflake rows for the course problems list."""
    table_name = get_qualified_table_name(PROBLEM_ANSWER_DISTRIBUTION_TABLE)
    sql = """
SELECT
    module_id,
    SUM(last_response_count) / COUNT(DISTINCT part_id) AS total_submissions,
    SUM(CASE WHEN correct = 1 THEN last_response_count ELSE 0 END) / COUNT(DISTINCT part_id)
        AS correct_submissions,
    LISTAGG(DISTINCT part_id, ',') WITHIN GROUP (ORDER BY part_id) AS part_ids,
    MAX(created) AS created
FROM {table_name}
WHERE course_id = %(course_id)s
GROUP BY module_id
ORDER BY module_id
""".format(table_name=table_name)

    return fetch_all(sql, {'course_id': course_id})


def get_problem_answer_distribution_rows(problem_id):
    """Return Snowflake rows for a problem answer distribution."""
    table_name = get_qualified_table_name(PROBLEM_ANSWER_DISTRIBUTION_TABLE)
    sql = """
SELECT
    course_id,
    module_id,
    part_id,
    correct,
    value_id,
    answer_value_text,
    variant,
    problem_display_name,
    question_text,
    first_response_count,
    last_response_count,
    created
FROM {table_name}
WHERE module_id = %(problem_id)s
ORDER BY part_id, value_id, variant
""".format(table_name=table_name)

    return fetch_all(sql, {'problem_id': problem_id})
