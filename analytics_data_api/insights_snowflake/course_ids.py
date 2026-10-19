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
        try:
            canonical_course_id = str(CourseKey.from_string(
                'course-v1:{}+{}+{}'.format(course_key.org, course_key.course, course_key.run)
            ))
        except InvalidKeyError:
            return course_id, None
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
        ' AND EQUAL_NULL({canonical_alias}.{column}, {alias}.{column})'.format(
            canonical_alias=canonical_alias,
            alias=alias,
            column=column,
        )
        for column in scope_columns
    )


def _placeholders(param_names):
    """Return the bound parameter placeholders for an IN list."""
    return ', '.join('%({})s'.format(param_name) for param_name in param_names)


def _is_plain_legacy_course_id(canonical_course_id, legacy_course_id):
    """Return whether the canonical ID is the legacy ID in ``course-v1`` form.

    The list filter rebuilds a legacy row's canonical ID in SQL, which only
    works for plain course keys. Keys with a branch or version keep their own
    clause.
    """
    return canonical_course_id == 'course-v1:{}'.format(legacy_course_id.replace('/', '+'))


def _course_id_clause(table_name, column_name, alias, scope_columns, index, canonical_param, legacy_param):
    """Build the filter for one logical course."""
    if legacy_param is None:
        return '({alias}.{column} = %({canonical_param})s)'.format(
            alias=alias,
            column=column_name,
            canonical_param=canonical_param,
        )

    canonical_alias = 'canonical_{}'.format(index)
    return (
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


def _course_id_list_clause(table_name, column_name, alias, scope_columns, canonical_params, legacy_params):
    """Build one filter for several logical courses.

    ``legacy_params`` maps the canonical parameter of each course that has a
    legacy form to its legacy parameter. A legacy row is matched to its
    canonical ID with the same expression as the unfiltered filter.
    """
    conditions = ['{alias}.{column} IN ({placeholders})'.format(
        alias=alias,
        column=column_name,
        placeholders=_placeholders(canonical_params),
    )]
    if legacy_params:
        conditions.append(
            '({alias}.{column} IN ({legacy_placeholders}) AND NOT EXISTS ('
            'SELECT 1 FROM {table_name} AS canonical '
            'WHERE canonical.{column} IN ({canonical_placeholders}) '
            "AND canonical.{column} = CONCAT('course-v1:', REPLACE({alias}.{column}, '/', '+'))"
            '{scope_clause}))'.format(
                alias=alias,
                column=column_name,
                legacy_placeholders=_placeholders(legacy_params.values()),
                table_name=table_name,
                canonical_placeholders=_placeholders(legacy_params.keys()),
                scope_clause=_scope_clause(alias, 'canonical', scope_columns),
            )
        )
    return '({})'.format(' OR '.join(conditions))


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

    Several courses share one IN filter and one subquery. Snowflake compile
    time grows with each subquery, and one subquery per course made requests
    for hundreds of courses hit the SQL compilation timeout.
    """
    if not course_ids:
        return '', {}

    params = {}
    clauses = []
    canonical_params = []
    legacy_params = {}
    unique_variants = list(dict.fromkeys(get_course_id_variants(course_id) for course_id in course_ids))

    for index, (canonical_course_id, legacy_course_id) in enumerate(unique_variants):
        canonical_param = '{}_{}_canonical'.format(param_prefix, index)
        params[canonical_param] = canonical_course_id
        legacy_param = None
        if legacy_course_id is not None:
            legacy_param = '{}_{}_legacy'.format(param_prefix, index)
            params[legacy_param] = legacy_course_id

        if len(unique_variants) == 1 or (
            legacy_param and not _is_plain_legacy_course_id(canonical_course_id, legacy_course_id)
        ):
            clauses.append(_course_id_clause(
                table_name, column_name, alias, scope_columns, index, canonical_param, legacy_param,
            ))
            continue

        canonical_params.append(canonical_param)
        if legacy_param:
            legacy_params[canonical_param] = legacy_param

    if canonical_params:
        clauses.insert(0, _course_id_list_clause(
            table_name, column_name, alias, scope_columns, canonical_params, legacy_params,
        ))

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
