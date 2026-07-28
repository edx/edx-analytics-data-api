"""
Helpers for the Insights Snowflake connection.

This module is intentionally not used by existing API views. Phase 1 only uses
it from a manual management command to validate deployed Snowflake connectivity.
"""

import re
from importlib import import_module

from cryptography.hazmat.primitives import serialization
from django.conf import settings

QUERY_TAG = 'edx_analytics_api_insights_snowflake_phase1'
DEFAULT_VALIDATION_TABLE = 'COURSE_ACTIVITY_WEEKLY'
REQUIRED_CONFIG_KEYS = (
    'ACCOUNT',
    'USER',
    'ROLE',
    'WAREHOUSE',
    'DATABASE',
    'SCHEMA',
    'PRIVATE_KEY',
)
IDENTIFIER_PATTERN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


class SnowflakeConfigurationError(Exception):
    """Raised when Insights Snowflake configuration is missing or unsafe."""


def get_insights_snowflake_config():
    """Return the configured Insights Snowflake settings."""
    config = getattr(settings, 'INSIGHTS_SNOWFLAKE', None)
    if not isinstance(config, dict):
        raise SnowflakeConfigurationError('INSIGHTS_SNOWFLAKE must be configured as a dictionary.')

    missing_keys = [key for key in REQUIRED_CONFIG_KEYS if not config.get(key)]
    if missing_keys:
        raise SnowflakeConfigurationError(
            'INSIGHTS_SNOWFLAKE is missing required settings: {}.'.format(', '.join(missing_keys))
        )

    return config


def get_private_key_der(config):
    """
    Convert the configured PEM private key string into DER bytes.

    edx-internal stores the Snowflake private key with literal "\\n" sequences.
    The connector expects a loaded private key serialized as DER/PKCS8 bytes.
    """
    private_key_value = config['PRIVATE_KEY']
    if not isinstance(private_key_value, str):
        raise SnowflakeConfigurationError('INSIGHTS_SNOWFLAKE PRIVATE_KEY must be a string.')

    normalized_private_key = private_key_value.replace('\\n', '\n').encode('utf-8')
    passphrase = config.get('PRIVATE_KEY_PASSPHRASE')
    passphrase_bytes = passphrase.encode('utf-8') if passphrase else None

    private_key = serialization.load_pem_private_key(
        normalized_private_key,
        password=passphrase_bytes,
    )

    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connect_to_insights_snowflake():
    """Open a Snowflake connection using the Insights Snowflake settings."""
    config = get_insights_snowflake_config()
    snowflake_connector = import_module('snowflake.connector')

    return snowflake_connector.connect(
        account=config['ACCOUNT'],
        user=config['USER'],
        role=config['ROLE'],
        warehouse=config['WAREHOUSE'],
        database=config['DATABASE'],
        schema=config['SCHEMA'],
        private_key=get_private_key_der(config),
        session_parameters={
            'QUERY_TAG': QUERY_TAG,
        },
    )


def validate_snowflake_identifier(identifier, label):
    """Return a safe Snowflake identifier or raise a sanitized error."""
    if not isinstance(identifier, str) or not IDENTIFIER_PATTERN.match(identifier):
        raise SnowflakeConfigurationError('Unsafe Snowflake {} identifier.'.format(label))
    return identifier.upper()


def run_read_only_query(sql):
    """Run a read-only Snowflake query and return all rows."""
    if not sql.lstrip().upper().startswith('SELECT '):
        raise SnowflakeConfigurationError('Only SELECT queries are allowed for Insights Snowflake validation.')

    connection = connect_to_insights_snowflake()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def get_table_row_count(table_name=DEFAULT_VALIDATION_TABLE):
    """Return the row count for a validated Snowflake table name."""
    config = get_insights_snowflake_config()
    database = validate_snowflake_identifier(config['DATABASE'], 'database')
    schema = validate_snowflake_identifier(config['SCHEMA'], 'schema')
    table = validate_snowflake_identifier(table_name, 'table')

    rows = run_read_only_query('SELECT COUNT(*) AS row_count FROM {}.{}.{}'.format(database, schema, table))
    return rows[0][0] if rows else 0
