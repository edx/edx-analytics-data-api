"""Map Snowflake program metadata rows into the existing API response shape."""

from itertools import groupby


def _row_value(row, name):
    """Return a row value from dictionary rows produced by the Snowflake client."""
    if name in row:
        return row[name]
    return row[name.upper()]


def map_program_metadata_rows(rows):
    """Group program metadata rows into one API item per program."""
    rows = sorted(rows or [], key=lambda row: (_row_value(row, 'program_id'), _row_value(row, 'course_id')))
    programs = []

    for program_id, group in groupby(rows, lambda row: _row_value(row, 'program_id')):
        item = {
            'program_id': program_id,
            'program_type': '',
            'program_title': '',
            'created': None,
            'course_ids': [],
        }

        for row in group:
            item['program_type'] = _row_value(row, 'program_type')
            item['program_title'] = _row_value(row, 'program_title')
            item['course_ids'].append(_row_value(row, 'course_id'))
            created = _row_value(row, 'created')
            item['created'] = max(created, item['created']) if item['created'] else created

        programs.append(item)

    return programs
