"""Map Snowflake performance rows into the existing API response shapes."""

from analytics_data_api.v0.models import ProblemFirstLastResponseAnswerDistribution

COURSE_PROBLEM_FIELDS = (
    'module_id',
    'total_submissions',
    'correct_submissions',
    'part_ids',
    'created',
)
COURSE_PROBLEM_INTEGER_FIELDS = (
    'total_submissions',
    'correct_submissions',
)


def _row_value(row, name):
    """Return a row value from dictionary rows produced by the Snowflake client."""
    if name in row:
        return row[name]
    return row[name.upper()]


def _optional_row_value(row, name):
    """Return a row value when present, otherwise None."""
    if name in row:
        return row[name]
    return row.get(name.upper())


def _nullable_int(value):
    """Return an integer value while preserving nulls."""
    if value is None:
        return None
    return int(value)


def _api_value(row, name):
    """Return the API-compatible value for a Snowflake course problem field."""
    value = _row_value(row, name)
    if name == 'part_ids':
        return value.split(',') if value else []
    if name in COURSE_PROBLEM_INTEGER_FIELDS:
        return int(value)
    return value


def _answer_value(row):
    """Return the Snowflake answer text using the existing API field name."""
    if 'answer_value_text' in row:
        return row['answer_value_text']
    if 'ANSWER_VALUE_TEXT' in row:
        return row['ANSWER_VALUE_TEXT']
    return _row_value(row, 'answer_value')


def _answer_sort_key(row):
    """Sort answer rows so existing part grouping is deterministic."""
    variant = _optional_row_value(row, 'variant')
    return (
        _row_value(row, 'part_id') or '',
        _row_value(row, 'value_id') or '',
        -1 if variant is None else int(variant),
    )


def map_course_problem_rows(rows):
    """Map Snowflake course problem rows into existing API response dictionaries."""
    return [
        {
            field: _api_value(row, field)
            for field in COURSE_PROBLEM_FIELDS
        }
        for row in rows or []
    ]


def map_problem_answer_distribution_rows(rows):
    """Map Snowflake answer distribution rows into unsaved model instances."""
    return [
        ProblemFirstLastResponseAnswerDistribution(
            course_id=_row_value(row, 'course_id'),
            module_id=_row_value(row, 'module_id'),
            part_id=_row_value(row, 'part_id'),
            correct=_row_value(row, 'correct'),
            value_id=_row_value(row, 'value_id'),
            answer_value=_answer_value(row),
            variant=_nullable_int(_optional_row_value(row, 'variant')),
            problem_display_name=_row_value(row, 'problem_display_name'),
            question_text=_row_value(row, 'question_text'),
            first_response_count=int(_row_value(row, 'first_response_count')),
            last_response_count=int(_row_value(row, 'last_response_count')),
            created=_row_value(row, 'created'),
        )
        for row in sorted(rows or [], key=_answer_sort_key)
    ]
