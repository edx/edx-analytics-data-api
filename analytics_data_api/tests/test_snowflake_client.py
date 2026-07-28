"""Tests for the temporary Insights Snowflake connectivity helper."""

from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from analytics_data_api.snowflake_client import (
    QUERY_TAG,
    SnowflakeConfigurationError,
    connect_to_insights_snowflake,
    get_insights_snowflake_config,
    get_private_key_der,
    get_table_row_count,
    run_read_only_query,
    validate_snowflake_identifier,
)


VALID_CONFIG = {
    'ACCOUNT': 'edx.us-east-1',
    'USER': 'INSIGHTS_API_SERVICE_USER',
    'ROLE': 'INSIGHTS_API_SERVICE_ROLE',
    'WAREHOUSE': 'INSIGHTS_API_SERVICE',
    'DATABASE': 'PROD',
    'SCHEMA': 'INSIGHTS',
    'PRIVATE_KEY': '-----BEGIN PRIVATE KEY-----\\nkey\\n-----END PRIVATE KEY-----',
    'PRIVATE_KEY_PASSPHRASE': None,
}


class SnowflakeClientTests(SimpleTestCase):
    """Cover the connection helper without making real Snowflake calls."""

    @override_settings(INSIGHTS_SNOWFLAKE=VALID_CONFIG)
    def test_get_insights_snowflake_config(self):
        self.assertEqual(get_insights_snowflake_config(), VALID_CONFIG)

    @override_settings(INSIGHTS_SNOWFLAKE=None)
    def test_get_insights_snowflake_config_requires_dictionary(self):
        with self.assertRaisesRegex(SnowflakeConfigurationError, 'must be configured as a dictionary'):
            get_insights_snowflake_config()

    @override_settings(INSIGHTS_SNOWFLAKE={})
    def test_get_insights_snowflake_config_requires_values(self):
        with self.assertRaisesRegex(SnowflakeConfigurationError, 'missing required settings'):
            get_insights_snowflake_config()

    def test_get_private_key_der_requires_string_key(self):
        config = dict(VALID_CONFIG, PRIVATE_KEY=None)

        with self.assertRaisesRegex(SnowflakeConfigurationError, 'PRIVATE_KEY must be a string'):
            get_private_key_der(config)

    @patch('analytics_data_api.snowflake_client.serialization.load_pem_private_key')
    def test_get_private_key_der_converts_key_and_passphrase(self, mock_load_pem_private_key):
        private_key = Mock()
        private_key.private_bytes.return_value = b'der-key'
        mock_load_pem_private_key.return_value = private_key
        config = dict(VALID_CONFIG, PRIVATE_KEY='line1\\nline2', PRIVATE_KEY_PASSPHRASE='passphrase')

        self.assertEqual(get_private_key_der(config), b'der-key')

        mock_load_pem_private_key.assert_called_once_with(b'line1\nline2', password=b'passphrase')

    @override_settings(INSIGHTS_SNOWFLAKE=VALID_CONFIG)
    @patch('analytics_data_api.snowflake_client.get_private_key_der')
    @patch('analytics_data_api.snowflake_client.import_module')
    def test_connect_to_insights_snowflake_uses_config(self, mock_import_module, mock_get_private_key_der):
        connector = Mock()
        mock_import_module.return_value = connector
        mock_get_private_key_der.return_value = b'der-key'

        connect_to_insights_snowflake()

        connector.connect.assert_called_once_with(
            account='edx.us-east-1',
            user='INSIGHTS_API_SERVICE_USER',
            role='INSIGHTS_API_SERVICE_ROLE',
            warehouse='INSIGHTS_API_SERVICE',
            database='PROD',
            schema='INSIGHTS',
            private_key=b'der-key',
            session_parameters={'QUERY_TAG': QUERY_TAG},
        )

    def test_validate_snowflake_identifier(self):
        self.assertEqual(validate_snowflake_identifier('course_activity_weekly', 'table'), 'COURSE_ACTIVITY_WEEKLY')

    def test_validate_snowflake_identifier_rejects_unsafe_values(self):
        with self.assertRaisesRegex(SnowflakeConfigurationError, 'Unsafe Snowflake table identifier'):
            validate_snowflake_identifier('course_activity_weekly;drop table users', 'table')

    def test_run_read_only_query_rejects_non_select_sql(self):
        with self.assertRaisesRegex(SnowflakeConfigurationError, 'Only SELECT queries are allowed'):
            run_read_only_query('DELETE FROM PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY')

    @patch('analytics_data_api.snowflake_client.connect_to_insights_snowflake')
    def test_run_read_only_query_closes_resources(self, mock_connect_to_insights_snowflake):
        cursor = Mock()
        cursor.fetchall.return_value = [(3,)]
        connection = Mock()
        connection.cursor.return_value = cursor
        mock_connect_to_insights_snowflake.return_value = connection

        self.assertEqual(run_read_only_query('SELECT 1'), [(3,)])

        cursor.execute.assert_called_once_with('SELECT 1')
        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()

    @override_settings(INSIGHTS_SNOWFLAKE=VALID_CONFIG)
    @patch('analytics_data_api.snowflake_client.run_read_only_query')
    def test_get_table_row_count(self, mock_run_read_only_query):
        mock_run_read_only_query.return_value = [(12,)]

        self.assertEqual(get_table_row_count('course_activity_weekly'), 12)

        mock_run_read_only_query.assert_called_once_with(
            'SELECT COUNT(*) AS row_count FROM PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY'
        )

    @override_settings(INSIGHTS_SNOWFLAKE=VALID_CONFIG)
    @patch('analytics_data_api.snowflake_client.run_read_only_query')
    def test_get_table_row_count_handles_empty_result(self, mock_run_read_only_query):
        mock_run_read_only_query.return_value = []

        self.assertEqual(get_table_row_count(), 0)
