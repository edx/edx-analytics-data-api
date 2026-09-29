"""Helpers for querying canonical and legacy edX course identifiers."""

from functools import lru_cache

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey


@lru_cache(maxsize=4096)
def get_course_id_variants(course_id):
    """Return the supported storage forms for a course key.

    Plain course locators have both a canonical ``course-v1`` form and a
    legacy slash form. Specialized CourseKey implementations, such as CCX
    keys, must remain exact because their additional identity cannot be
    represented by the plain course forms.
    """
    course_key = CourseKey.from_string(course_id)
    is_legacy_course_id = isinstance(course_id, str) and course_id.count('/') == 2 and ':' not in course_id
    if is_legacy_course_id:
        canonical_course_id = str(CourseKey.from_string(
            'course-v1:{}+{}+{}'.format(course_key.org, course_key.course, course_key.run)
        ))
        return canonical_course_id, course_id

    canonical_course_id = str(course_key)
    if not canonical_course_id.startswith('course-v1:'):
        return canonical_course_id, None

    legacy_course_id = '/'.join((course_key.org, course_key.course, course_key.run))
    return canonical_course_id, legacy_course_id


def get_canonical_course_id(course_id):
    """Return the canonical course ID for either supported representation."""
    return get_course_id_variants(course_id)[0]


def get_response_course_id(course_id):
    """Normalize a stored course ID without failing on malformed data."""
    try:
        return get_canonical_course_id(course_id)
    except (InvalidKeyError, TypeError):
        return course_id


def _scope_clause(alias, canonical_alias, scope_columns):
    """Build fixed-column equality predicates for format preference."""
    return ''.join(
        ' AND {canonical_alias}.{column} = {alias}.{column}'.format(
            canonical_alias=canonical_alias,
            alias=alias,
            column=column,
        )
        for column in scope_columns
    )


def build_preferred_course_id_filter(
    table_name,
    column_name,
    course_ids,
    alias='source',
    param_prefix='course_id',
    prefix='WHERE',
    scope_columns=(),
):
    """Build a parameterized filter that prefers canonical course IDs.

    A legacy row is selected only when no canonical row exists for the same
    logical course and scope in the source table. Scope columns allow daily,
    interval, mode, and other reporting grains to retain data when formats are
    split across periods. Table, column, and scope names are supplied by the
    query modules from fixed constants, while course IDs remain bound
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

        if legacy_course_id is None:
            clauses.append('({alias}.{column} = %({canonical_param})s)'.format(
                alias=alias,
                column=column_name,
                canonical_param=canonical_param,
            ))
            continue

        params[legacy_param] = legacy_course_id
        clauses.append(
            '({alias}.{column} = %({canonical_param})s '
            'OR ({alias}.{column} = %({legacy_param})s AND NOT EXISTS ('
            'SELECT 1 FROM {table_name} AS {canonical_alias} '
            'WHERE {canonical_alias}.{column} = %({canonical_param})s'
            '{scope_clause})))'.format(
                alias=alias,
                column=column_name,
                canonical_param=canonical_param,
                legacy_param=legacy_param,
                table_name=table_name,
                canonical_alias=canonical_alias,
                scope_clause=_scope_clause(alias, canonical_alias, scope_columns),
            )
        )

    condition = clauses[0] if len(clauses) == 1 else '({})'.format(' OR '.join(clauses))
    return '{} {}'.format(prefix, condition) if prefix else condition, params


def build_unfiltered_course_id_filter(
    table_name,
    column_name,
    alias='source',
    prefix='WHERE',
    scope_columns=(),
):
    """Build a filter that prefers canonical rows for an unfiltered query.

    This is intentionally limited to the plain slash-to-``course-v1`` storage
    relationship. Specialized keys and null values are retained unchanged.
    """
    canonical_alias = 'canonical'
    condition = (
        '({alias}.{column} IS NULL '
        "OR POSITION('/' IN {alias}.{column}) = 0 "
        'OR NOT EXISTS ('
        'SELECT 1 FROM {table_name} AS {canonical_alias} '
        "WHERE {canonical_alias}.{column} = CONCAT('course-v1:', REPLACE({alias}.{column}, '/', '+'))"
        '{scope_clause})'
        ')'
    ).format(
        alias=alias,
        column=column_name,
        table_name=table_name,
        canonical_alias=canonical_alias,
        scope_clause=_scope_clause(alias, canonical_alias, scope_columns),
    )
    return '{} {}'.format(prefix, condition) if prefix else condition, {}
