"""Validate the Insights Snowflake connection from the deployed Analytics API service."""

from django.core.management.base import BaseCommand, CommandError

from analytics_data_api.snowflake_client import (
    DEFAULT_VALIDATION_TABLE,
    SnowflakeConfigurationError,
    get_insights_snowflake_config,
    get_table_row_count,
)


class Command(BaseCommand):
    """Run a manual read-only Snowflake connectivity check."""

    help = 'Validate Insights Snowflake connectivity with a read-only query.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--table',
            default=DEFAULT_VALIDATION_TABLE,
            help='Snowflake table to count for validation. Defaults to COURSE_ACTIVITY_WEEKLY.',
        )

    def handle(self, *args, **options):
        table = options['table']

        try:
            config = get_insights_snowflake_config()
            row_count = get_table_row_count(table)
        except SnowflakeConfigurationError as exc:
            raise CommandError(str(exc))
        except Exception as exc:  # pylint: disable=broad-except
            raise CommandError('Insights Snowflake connectivity check failed: {}'.format(exc))

        self.stdout.write('Insights Snowflake connectivity check succeeded.')
        self.stdout.write('Account: {}'.format(config['ACCOUNT']))
        self.stdout.write('User: {}'.format(config['USER']))
        self.stdout.write('Role: {}'.format(config['ROLE']))
        self.stdout.write('Warehouse: {}'.format(config['WAREHOUSE']))
        self.stdout.write('Database: {}'.format(config['DATABASE']))
        self.stdout.write('Schema: {}'.format(config['SCHEMA']))
        self.stdout.write('Table: {}'.format(table))
        self.stdout.write('Row count: {}'.format(row_count))
