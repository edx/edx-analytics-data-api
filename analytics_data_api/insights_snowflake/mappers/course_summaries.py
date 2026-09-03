"""Map Snowflake course summary rows into the existing API response shape."""

from itertools import groupby

from analytics_data_api.constants import enrollment_modes

COUNT_FIELDS = ('count', 'cumulative_count', 'count_change_7_days', 'passing_users')
SUMMARY_META_FIELDS = (
    'catalog_course_title',
    'catalog_course',
    'start_time',
    'end_time',
    'pacing_type',
    'availability',
)


def _row_value(row, name):
    """Return a row value from dictionary rows produced by the Snowflake client."""
    if name in row:
        return row[name]
    return row[name.upper()]


def _count_value(row, name):
    """Return an integer count, treating missing nullable Snowflake counts as zero."""
    return int(_row_value(row, name) or 0)


def _base_course_summary(course_id):
    """Return the default course summary shape used by the existing API."""
    summary = {
        'course_id': course_id,
        'created': None,
        'enrollment_modes': {},
    }
    summary.update({field: 0 for field in COUNT_FIELDS})
    summary['enrollment_modes'].update({
        mode: {
            count_field: 0 for count_field in COUNT_FIELDS
        } for mode in enrollment_modes.ALL
    })
    return summary


def _programs_by_course(program_rows):
    """Return program IDs grouped by course ID."""
    programs = {}
    for row in program_rows or []:
        programs.setdefault(_row_value(row, 'course_id'), []).append(_row_value(row, 'program_id'))
    return programs


def _recent_counts_by_course(recent_rows):
    """Return recent enrollment counts keyed by course ID."""
    return {
        _row_value(row, 'course_id'): _count_value(row, 'count')
        for row in recent_rows or []
    }


def _postprocess_course_summary(summary, exclude=None):
    """Apply existing course summary response compatibility rules."""
    modes = summary['enrollment_modes']
    prof_no_id_mode = modes.pop(enrollment_modes.PROFESSIONAL_NO_ID, {})
    prof_mode = modes[enrollment_modes.PROFESSIONAL]
    for count_key in COUNT_FIELDS:
        prof_mode[count_key] = prof_mode.get(count_key, 0) + prof_no_id_mode.pop(count_key, 0)

    if summary['availability'] == 'Starting Soon':
        summary['availability'] = 'Upcoming'

    for field in exclude or []:
        for mode in summary['enrollment_modes']:
            summary['enrollment_modes'][mode].pop(field, None)

    return summary


def map_course_summary_rows(summary_rows, program_rows=None, recent_rows=None, exclude=None):
    """Group course summary rows into one API item per course."""
    rows = sorted(
        summary_rows or [],
        key=lambda row: (_row_value(row, 'course_id'), _row_value(row, 'enrollment_mode')),
    )
    programs = _programs_by_course(program_rows) if program_rows is not None else None
    recent_counts = _recent_counts_by_course(recent_rows) if recent_rows is not None else None
    summaries = []

    for course_id, group in groupby(rows, lambda row: _row_value(row, 'course_id')):
        summary = _base_course_summary(course_id)

        for row in group:
            for field in SUMMARY_META_FIELDS:
                summary[field] = _row_value(row, field)

            mode = _row_value(row, 'enrollment_mode')
            summary['enrollment_modes'][mode] = {field: _count_value(row, field) for field in COUNT_FIELDS}
            created = _row_value(row, 'created')
            summary['created'] = max(created, summary['created']) if summary['created'] else created
            summary.update({
                field: summary[field] + _count_value(row, field)
                for field in COUNT_FIELDS
            })

        if recent_counts is not None:
            summary['recent_count_change'] = summary['count'] - recent_counts.get(course_id, 0)

        if programs is not None:
            summary['programs'] = programs.get(course_id, [])

        summaries.append(_postprocess_course_summary(summary, exclude=exclude))

    return summaries
