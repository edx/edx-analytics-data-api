"""Endpoint-safe Snowflake client helpers for Insights."""

from analytics_data_api.monitoring import trace_snowflake_connection, trace_snowflake_query
from analytics_data_api.snowflake_client import (
    SnowflakeConfigurationError,
    SnowflakeQueryTimeoutError,
    connect_to_insights_snowflake,
    get_insights_snowflake_config,
    get_insights_snowflake_query_timeout,
    validate_snowflake_identifier,
)

# The SQLSTATE of a statement that Snowflake canceled, for example when the query timeout ran out.
QUERY_CANCELED_SQLSTATE = '57014'


def get_qualified_table_name(table_name):
    """Return a configured, validated Snowflake table reference."""
    config = get_insights_snowflake_config()
    database = validate_snowflake_identifier(config['DATABASE'], 'database')
    schema = validate_snowflake_identifier(config['SCHEMA'], 'schema')
    table = validate_snowflake_identifier(table_name, 'table')

    return '{}.{}.{}'.format(database, schema, table)


def fetch_all(sql, params=None, table_name=None):
    """Run a read-only Snowflake query and return rows as dictionaries."""
    tokens = sql.lstrip().split(None, 1)
    if not tokens or tokens[0].upper() != 'SELECT':
        raise SnowflakeConfigurationError('Only SELECT queries are allowed for Insights Snowflake endpoints.')

    timeout = get_insights_snowflake_query_timeout()
    connection = None
    cursor = None
    try:
        table_name = table_name or 'unknown'
        with trace_snowflake_connection(table_name):
            connection = connect_to_insights_snowflake()
        with trace_snowflake_query(table_name):
            cursor = connection.cursor()
            cursor.execute(sql, params or {}, timeout=timeout)
            column_names = [column[0].lower() for column in cursor.description]
            return [
                dict(zip(column_names, row))
                for row in cursor.fetchall()
            ]
    except Exception as error:
        # The query span has already recorded the Snowflake error. The request gets a timeout error instead of a 500.
        if getattr(error, 'sqlstate', None) == QUERY_CANCELED_SQLSTATE:
            raise SnowflakeQueryTimeoutError(
                'Snowflake canceled the {} query, usually because it ran longer than {} seconds.'.format(
                    table_name, timeout,
                )
            ) from error
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
