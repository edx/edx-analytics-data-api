"""Tests for the temporary Insights Snowflake smoke-test command."""

from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from analytics_data_api.snowflake_client import SnowflakeConfigurationError


VALID_CONFIG = {
    'ACCOUNT': 'edx.us-east-1',
    'USER': 'INSIGHTS_API_SERVICE_USER',
    'ROLE': 'INSIGHTS_API_SERVICE_ROLE',
    'WAREHOUSE': 'INSIGHTS_API_SERVICE',
    'DATABASE': 'PROD',
    'SCHEMA': 'INSIGHTS',
    'PRIVATE_KEY': 'secret-private-key',
}


class CheckInsightsSnowflakeCommandTests(SimpleTestCase):
    """
    Cover the Phase 1 smoke-test command.

    Remove these tests with the command after Snowflake connectivity validation
    is complete and endpoint migration owns the connection path.
    """

    @patch('analytics_data_api.management.commands.check_insights_snowflake.get_table_row_count')
    @patch('analytics_data_api.management.commands.check_insights_snowflake.get_insights_snowflake_config')
    def test_command_prints_non_secret_connection_context(self, mock_get_config, mock_get_table_row_count):
        mock_get_config.return_value = VALID_CONFIG
        mock_get_table_row_count.return_value = 42
        stdout = StringIO()

        call_command('check_insights_snowflake', '--table', 'COURSE_ACTIVITY_WEEKLY', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('Insights Snowflake connectivity check succeeded.', output)
        self.assertIn('Account: edx.us-east-1', output)
        self.assertIn('User: INSIGHTS_API_SERVICE_USER', output)
        self.assertIn('Role: INSIGHTS_API_SERVICE_ROLE', output)
        self.assertIn('Warehouse: INSIGHTS_API_SERVICE', output)
        self.assertIn('Database: PROD', output)
        self.assertIn('Schema: INSIGHTS', output)
        self.assertIn('Table: COURSE_ACTIVITY_WEEKLY', output)
        self.assertIn('Row count: 42', output)
        self.assertNotIn('secret-private-key', output)
        mock_get_table_row_count.assert_called_once_with('COURSE_ACTIVITY_WEEKLY')

    @patch('analytics_data_api.management.commands.check_insights_snowflake.get_insights_snowflake_config')
    def test_command_raises_config_errors(self, mock_get_config):
        mock_get_config.side_effect = SnowflakeConfigurationError('missing config')

        with self.assertRaisesRegex(CommandError, 'missing config'):
            call_command('check_insights_snowflake')

    @patch('analytics_data_api.management.commands.check_insights_snowflake.get_table_row_count')
    @patch('analytics_data_api.management.commands.check_insights_snowflake.get_insights_snowflake_config')
    def test_command_wraps_unexpected_errors(self, mock_get_config, mock_get_table_row_count):
        mock_get_config.return_value = VALID_CONFIG
        mock_get_table_row_count.side_effect = RuntimeError('snowflake unavailable')

        with self.assertRaisesRegex(CommandError, 'Insights Snowflake connectivity check failed'):
            call_command('check_insights_snowflake')
