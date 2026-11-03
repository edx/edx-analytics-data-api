"""Map Snowflake course summary rows into the existing API response shape."""

import datetime
from itertools import groupby

from opaque_keys import InvalidKeyError

from analytics_data_api.constants import enrollment_modes
from analytics_data_api.insights_snowflake.course_ids import get_course_id_variants, get_response_course_id

COUNT_FIELDS = ('count', 'cumulative_count', 'count_change_7_days', 'passing_users')
SUMMARY_META_FIELDS = (
    'catalog_course_title',
    'catalog_course',
    'start_time',
    'end_time',
    'pacing_type',
    'availability',
)
# The counts that follow a date range: the count on its end date, and the enrollments made in it (cumulative_count).
RANGE_COUNT_FIELDS = ('count', 'cumulative_count')
# Fields that have no data by date yet. With a date range they are None, so a response never mixes the range with
# all-time values.
FIELDS_WITHOUT_RANGE_DATA = (
    'b2b_count',
    'b2c_count',
    'subscription_count',
    'alacarte_count',
    'sales_model',
    'funding_model',
    'total_engagements',
    'engagement_rate',
)


def _row_value(row, name):
    """Return a row value from dictionary rows produced by the Snowflake client."""
    if name in row:
        return row[name]
    return row[name.upper()]


def _count_value(row, name):
    """Return an integer count, treating missing nullable Snowflake counts as zero."""
    return int(_row_value(row, name) or 0)


def _optional_row_value(row, name):
    """Return a row value when present, otherwise None for defensive deduplication."""
    return row.get(name, row.get(name.upper()))


def _course_id(row):
    """Return the canonical course ID from a Snowflake row."""
    return get_response_course_id(_row_value(row, 'course_id'))


def _drop_legacy_rows_when_canonical_exists(rows, scope_fields):
    """Drop duplicate legacy rows while preserving specialized and invalid IDs."""
    rows = list(rows or [])
    canonical_keys = set()
    row_details = []

    for row in rows:
        raw_course_id = _row_value(row, 'course_id')
        try:
            canonical_course_id, legacy_course_id = get_course_id_variants(raw_course_id)
        except (InvalidKeyError, TypeError):
            row_details.append((row, raw_course_id, None, None, None))
            continue

        scope = tuple(_optional_row_value(row, field) for field in scope_fields)
        row_details.append((row, raw_course_id, canonical_course_id, legacy_course_id, scope))
        if legacy_course_id is not None and raw_course_id == canonical_course_id:
            canonical_keys.add((canonical_course_id, scope))

    return [
        row for row, raw_course_id, canonical_course_id, legacy_course_id, scope in row_details
        if not (legacy_course_id is not None and
                raw_course_id == legacy_course_id and
                (canonical_course_id, scope) in canonical_keys)
    ]


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
    program_rows = _drop_legacy_rows_when_canonical_exists(program_rows, ('program_id',))
    for row in program_rows:
        programs.setdefault(_course_id(row), []).append(_row_value(row, 'program_id'))
    return programs


def _recent_counts_by_course(recent_rows):
    """Return recent enrollment counts keyed by course ID."""
    recent_rows = _drop_legacy_rows_when_canonical_exists(recent_rows, ('date',))
    return {
        _course_id(row): _count_value(row, 'count')
        for row in recent_rows or []
    }


def _date(value):
    """Return a Snowflake date or timestamp value as a date."""
    if isinstance(value, datetime.datetime):
        return value.date()
    return value


def _range_counts(range_rows, range_window, scope_fields):
    """Return {(course ID, *scope): {'start': counts, 'end': counts}} for a date range.

    range_window is (the day before the range starts, the day it ends). The counts on each of those days are
    {'count': ..., 'cumulative_count': ...}; a course or mode without a row on a day has no entry for it.
    """
    if not range_window:
        return {}
    before_start, end = range_window
    counts = {}
    range_rows = _drop_legacy_rows_when_canonical_exists(range_rows, ('date',) + scope_fields)
    for row in range_rows:
        key = (_course_id(row),) + tuple(_row_value(row, field) for field in scope_fields)
        values = {field: _count_value(row, field) for field in RANGE_COUNT_FIELDS}
        date = _date(_row_value(row, 'date'))
        if date == before_start:
            counts.setdefault(key, {})['start'] = values
        if date == end:
            counts.setdefault(key, {})['end'] = values
    return counts


def _counts_in_range(counts):
    """Return the count on the range's end date and the enrollments made in the range (0 without rows)."""
    counts = counts or {}
    start = counts.get('start', {})
    end = counts.get('end', {})
    return {
        'count': end.get('count', 0),
        'cumulative_count': end.get('cumulative_count', 0) - start.get('cumulative_count', 0),
    }


def _apply_date_range(summary, course_counts, mode_counts):
    """Replace the counts of a summary with those of the date range; the other fields stay as they are."""
    course_id = summary['course_id']
    summary.update(_counts_in_range(course_counts.get((course_id,))))
    for mode, mode_summary in summary['enrollment_modes'].items():
        mode_summary.update(_counts_in_range(mode_counts.get((course_id, mode))))


def _clear_fields_without_range_data(summary):
    """Set to None the fields that can't follow a date range yet (see FIELDS_WITHOUT_RANGE_DATA)."""
    for field in FIELDS_WITHOUT_RANGE_DATA:
        if field in summary:
            summary[field] = None


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


def map_course_summary_rows(  # pylint: disable=too-many-positional-arguments
        summary_rows,
        program_rows=None,
        recent_rows=None,
        exclude=None,
        range_rows=None,
        range_mode_rows=None,
        range_window=None,
):
    """Group course summary rows into one API item per course.

    With a date range (range_rows not None), count and cumulative_count, in total and per mode, are those of the
    range: the count on its end date and the enrollments made in it. range_rows and range_mode_rows are the course
    and mode enrollment rows on the dates of range_window: (the day before the range starts, the day it ends). The
    window is None when there is no enrollment data at all, and every range count is then 0.
    """
    summary_rows = _drop_legacy_rows_when_canonical_exists(summary_rows, ('enrollment_mode',))
    rows = sorted(
        summary_rows or [],
        key=lambda row: (
            _course_id(row) or '',
            _row_value(row, 'enrollment_mode') or '',
        ),
    )
    programs = _programs_by_course(program_rows) if program_rows is not None else None
    recent_counts = _recent_counts_by_course(recent_rows) if recent_rows is not None else None
    has_date_range = range_rows is not None
    if has_date_range:
        course_range_counts = _range_counts(range_rows, range_window, ())
        mode_range_counts = _range_counts(range_mode_rows or [], range_window, ('mode',))
    summaries = []

    for course_id, group in groupby(rows, _course_id):
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

        if has_date_range:
            _apply_date_range(summary, course_range_counts, mode_range_counts)

        if recent_counts is not None:
            summary['recent_count_change'] = summary['count'] - recent_counts.get(course_id, 0)

        if programs is not None:
            summary['programs'] = programs.get(course_id, [])

        summary = _postprocess_course_summary(summary, exclude=exclude)
        if has_date_range:
            _clear_fields_without_range_data(summary)
        summaries.append(summary)

    return summaries
