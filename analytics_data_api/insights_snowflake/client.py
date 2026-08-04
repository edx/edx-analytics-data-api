"""Endpoint-safe Snowflake client helpers for Insights."""

from analytics_data_api.snowflake_client import (
    SnowflakeConfigurationError,
    connect_to_insights_snowflake,
    get_insights_snowflake_config,
    validate_snowflake_identifier,
)


def get_qualified_table_name(table_name):
    """Return a configured, validated Snowflake table reference."""
    config = get_insights_snowflake_config()
    database = validate_snowflake_identifier(config['DATABASE'], 'database')
    schema = validate_snowflake_identifier(config['SCHEMA'], 'schema')
    table = validate_snowflake_identifier(table_name, 'table')

    return '{}.{}.{}'.format(database, schema, table)


def fetch_all(sql, params=None):
    """Run a read-only Snowflake query and return rows as dictionaries."""
    tokens = sql.lstrip().split(None, 1)
    if not tokens or tokens[0].upper() != 'SELECT':
        raise SnowflakeConfigurationError('Only SELECT queries are allowed for Insights Snowflake endpoints.')

    connection = connect_to_insights_snowflake()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params or {})
        column_names = [column[0].lower() for column in cursor.description]
        return [
            dict(zip(column_names, row))
            for row in cursor.fetchall()
        ]
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
