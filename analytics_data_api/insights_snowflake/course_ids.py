"""Helpers for querying canonical and legacy edX course identifiers."""

from opaque_keys.edx.keys import CourseKey


def get_course_id_variants(course_id):
    """Return the canonical and legacy string forms for a course key."""
    course_key = CourseKey.from_string(course_id)
    canonical_course_id = str(CourseKey.from_string(
        'course-v1:{}+{}+{}'.format(course_key.org, course_key.course, course_key.run)
    ))
    legacy_course_id = '/'.join((course_key.org, course_key.course, course_key.run))
    return canonical_course_id, legacy_course_id


def get_canonical_course_id(course_id):
    """Return the canonical course ID for either supported representation."""
    return get_course_id_variants(course_id)[0]


def build_preferred_course_id_filter(
    table_name,
    column_name,
    course_ids,
    alias='source',
    param_prefix='course_id',
    prefix='WHERE',
):
    """Build a parameterized filter that prefers canonical course IDs.

    A legacy row is selected only when no canonical row exists for the same
    logical course in the source table. Table and column names are supplied by
    the query modules from fixed constants, while course IDs remain bound
    parameters.
    """
    if not course_ids:
        return '', {}

    params = {}
    clauses = []
    seen_variants = set()

    for course_id in course_ids:
        canonical_course_id, legacy_course_id = get_course_id_variants(course_id)
        variants = (canonical_course_id, legacy_course_id)
        if variants in seen_variants:
            continue
        seen_variants.add(variants)

        index = len(clauses)
        canonical_param = '{}_{}_canonical'.format(param_prefix, index)
        legacy_param = '{}_{}_legacy'.format(param_prefix, index)
        canonical_alias = 'canonical_{}'.format(index)
        params[canonical_param] = canonical_course_id
        params[legacy_param] = legacy_course_id

        clauses.append(
            '({alias}.{column} = %({canonical_param})s '
            'OR ({alias}.{column} = %({legacy_param})s AND NOT EXISTS ('
            'SELECT 1 FROM {table_name} AS {canonical_alias} '
            'WHERE {canonical_alias}.{column} = %({canonical_param})s)))'.format(
                alias=alias,
                column=column_name,
                canonical_param=canonical_param,
                legacy_param=legacy_param,
                table_name=table_name,
                canonical_alias=canonical_alias,
            )
        )

    condition = '({})'.format(' OR '.join(clauses))
    return '{} {}'.format(prefix, condition) if prefix else condition, params
