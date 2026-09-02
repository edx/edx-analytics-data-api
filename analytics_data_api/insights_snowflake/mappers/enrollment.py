"""Map Snowflake enrollment rows into the existing API response shapes."""

from itertools import groupby

from analytics_data_api.constants import enrollment_modes, genders
from analytics_data_api.v0 import models

GENDER_FIELD_MAP = {
    'f': genders.FEMALE,
    genders.FEMALE: genders.FEMALE,
    'm': genders.MALE,
    genders.MALE: genders.MALE,
    'o': genders.OTHER,
    genders.OTHER: genders.OTHER,
}


def _row_value(row, name):
    """Return a row value from dictionary rows produced by the Snowflake client."""
    if name in row:
        return row[name]
    return row[name.upper()]


def _copy_fields(row, field_names):
    """Return an API-shaped dictionary with selected fields from a Snowflake row."""
    return {
        field_name: _row_value(row, field_name)
        for field_name in field_names
    }


def _gender_field(gender):
    """Return the existing API gender field for a Snowflake gender value."""
    if gender is None:
        return genders.UNKNOWN
    return GENDER_FIELD_MAP.get(gender.lower(), genders.UNKNOWN)


def map_course_enrollment_daily_rows(rows):
    """Map course enrollment count rows into the existing API shape."""
    return [
        _copy_fields(row, ['course_id', 'date', 'count', 'created'])
        for row in rows or []
    ]


def map_course_enrollment_education_rows(rows):
    """Map enrollment education rows into the existing API shape."""
    return [
        _copy_fields(row, ['course_id', 'date', 'education_level', 'count', 'created'])
        for row in rows or []
    ]


def map_course_enrollment_mode_rows(rows):
    """Pivot enrollment mode rows into the existing API shape."""
    rows = sorted(rows or [], key=lambda row: (_row_value(row, 'course_id'), _row_value(row, 'date')))
    formatted_data = []

    for key, group in groupby(rows, lambda row: (_row_value(row, 'course_id'), _row_value(row, 'date'))):
        item = {
            'course_id': key[0],
            'date': key[1],
            'created': None,
        }
        total = 0
        cumulative_total = 0

        for row in group:
            mode = _row_value(row, 'mode')
            count = int(_row_value(row, 'count'))
            cumulative_count = int(_row_value(row, 'cumulative_count'))
            created = _row_value(row, 'created')
            item[mode] = item.get(mode, 0) + count
            item['created'] = max(created, item['created']) if item['created'] else created
            total += count
            cumulative_total += cumulative_count

        item[enrollment_modes.PROFESSIONAL] = item.get(enrollment_modes.PROFESSIONAL, 0) + item.pop(
            enrollment_modes.PROFESSIONAL_NO_ID,
            0,
        )
        item['count'] = total
        item['cumulative_count'] = cumulative_total
        formatted_data.append(item)

    return formatted_data


def map_course_enrollment_gender_rows(rows):
    """Pivot enrollment gender rows into the existing API shape."""
    rows = sorted(rows or [], key=lambda row: (_row_value(row, 'course_id'), _row_value(row, 'date')))
    formatted_data = []

    for key, group in groupby(rows, lambda row: (_row_value(row, 'course_id'), _row_value(row, 'date'))):
        item = {
            'course_id': key[0],
            'date': key[1],
            'created': None,
            genders.MALE: 0,
            genders.FEMALE: 0,
            genders.OTHER: 0,
            genders.UNKNOWN: 0,
        }

        for row in group:
            gender = _gender_field(_row_value(row, 'gender'))
            created = _row_value(row, 'created')
            item[gender] += int(_row_value(row, 'count'))
            item['created'] = max(created, item['created']) if item['created'] else created

        formatted_data.append(item)

    return formatted_data


def map_course_enrollment_location_rows(rows):
    """Map enrollment location rows into model instances used by the current serializer."""
    items = [
        models.CourseEnrollmentByCountry(
            course_id=_row_value(row, 'course_id'),
            date=_row_value(row, 'date'),
            country_code=_row_value(row, 'country_code'),
            count=int(_row_value(row, 'count')),
            created=_row_value(row, 'created'),
        )
        for row in rows or []
    ]
    items = sorted(items, key=lambda item: '' if item.country.alpha2 is None else item.country.alpha2)
    returned_items = []

    for key, group in groupby(items, lambda item: (item.date, item.country.alpha2, item.course_id)):
        count = 0
        created = None

        for item in group:
            created = max(created, item.created) if created else item.created
            count += item.count

        returned_items.append(models.CourseEnrollmentByCountry(
            course_id=key[2],
            date=key[0],
            country_code=key[1],
            count=count,
            created=created,
        ))

    return returned_items
