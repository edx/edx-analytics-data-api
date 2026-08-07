"""Tests for Snowflake-backed Insights endpoint helpers."""

import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name
from analytics_data_api.insights_snowflake.mappers.activity import map_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.queries.activity import get_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.service import get_course_activity_weekly
from analytics_data_api.insights_snowflake.toggles import (
    COURSE_ACTIVITY_SNOWFLAKE_FLAG,
    is_course_activity_snowflake_enabled,
)
from analytics_data_api.snowflake_client import SnowflakeConfigurationError

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


class InsightsSnowflakeClientTests(SimpleTestCase):
    """Cover endpoint-safe Snowflake client helpers without real Snowflake calls."""

    @override_settings(INSIGHTS_SNOWFLAKE=VALID_CONFIG)
    def test_get_qualified_table_name(self):
        self.assertEqual(get_qualified_table_name('course_activity_weekly'), 'PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY')

    def test_fetch_all_rejects_non_select_sql(self):
        with self.assertRaisesRegex(SnowflakeConfigurationError, 'Only SELECT queries are allowed'):
            fetch_all('DELETE FROM PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY')

    @patch('analytics_data_api.insights_snowflake.client.connect_to_insights_snowflake')
    def test_fetch_all_returns_dictionary_rows_and_closes_resources(self, mock_connect_to_insights_snowflake):
        cursor = Mock()
        cursor.description = [('COURSE_ID',), ('ACTIVITY_COUNT',)]
        cursor.fetchall.return_value = [('course-v1:edX+DemoX+Demo_Course', 3)]
        connection = Mock()
        connection.cursor.return_value = cursor
        mock_connect_to_insights_snowflake.return_value = connection
        params = {'course_id': 'course-v1:edX+DemoX+Demo_Course'}

        rows = fetch_all('SELECT course_id, count FROM PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY', params)

        self.assertEqual(rows, [{'course_id': 'course-v1:edX+DemoX+Demo_Course', 'activity_count': 3}])
        cursor.execute.assert_called_once_with(
            'SELECT course_id, count FROM PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY',
            params,
        )
        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()


class InsightsSnowflakeActivityQueryTests(SimpleTestCase):
    """Cover course activity query construction with mocked Snowflake execution."""

    @patch('analytics_data_api.insights_snowflake.queries.activity.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.activity.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY')
    )
    def test_get_course_activity_weekly_rows_uses_latest_week_query_without_dates(self, mock_fetch_all):
        mock_fetch_all.return_value = [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}]

        rows = get_course_activity_weekly_rows('course-v1:edX+DemoX+Demo_Course')

        self.assertEqual(rows, [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}])
        sql, params = mock_fetch_all.call_args[0]
        self.assertIn('SELECT MAX(interval_end)', sql)
        self.assertEqual(params, {'course_id': 'course-v1:edX+DemoX+Demo_Course'})

    @patch('analytics_data_api.insights_snowflake.queries.activity.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.activity.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_ACTIVITY_WEEKLY')
    )
    def test_get_course_activity_weekly_rows_uses_date_range_query_with_dates(self, mock_fetch_all):
        start_date = datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2014, 1, 8, tzinfo=datetime.timezone.utc)

        get_course_activity_weekly_rows(
            'course-v1:edX+DemoX+Demo_Course',
            start_date=start_date,
            end_date=end_date,
        )

        sql, params = mock_fetch_all.call_args[0]
        self.assertIn('interval_start >= %(start_date)s', sql)
        self.assertIn('interval_end < %(end_date)s', sql)
        self.assertEqual(params, {
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'start_date': start_date,
            'end_date': end_date,
        })


class InsightsSnowflakeActivityMapperTests(SimpleTestCase):
    """Cover Snowflake activity row mapping into the existing API shape."""

    def test_map_course_activity_weekly_rows_pivots_activity_labels(self):
        interval_start = datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc)
        interval_end = datetime.datetime(2014, 1, 8, tzinfo=datetime.timezone.utc)
        created = datetime.datetime(2014, 1, 9, tzinfo=datetime.timezone.utc)
        later_created = datetime.datetime(2014, 1, 10, tzinfo=datetime.timezone.utc)

        rows = [
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'interval_start': interval_start,
                'interval_end': interval_end,
                'activity_label': 'PLAYED_VIDEO',
                'activity_count': 400,
                'created': later_created,
            },
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'interval_start': interval_start,
                'interval_end': interval_end,
                'activity_label': 'ACTIVE',
                'activity_count': 300,
                'created': created,
            },
        ]

        self.assertEqual(map_course_activity_weekly_rows(rows), [{
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'interval_start': interval_start,
            'interval_end': interval_end,
            'created': later_created,
            'played_video': 400,
            'any': 300,
        }])

    def test_map_course_activity_weekly_rows_accepts_uppercase_snowflake_keys(self):
        interval_start = datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc)
        interval_end = datetime.datetime(2014, 1, 8, tzinfo=datetime.timezone.utc)
        created = datetime.datetime(2014, 1, 9, tzinfo=datetime.timezone.utc)

        rows = [{
            'COURSE_ID': 'course-v1:edX+DemoX+Demo_Course',
            'INTERVAL_START': interval_start,
            'INTERVAL_END': interval_end,
            'ACTIVITY_LABEL': 'ACTIVE',
            'ACTIVITY_COUNT': 300,
            'CREATED': created,
        }]

        self.assertEqual(map_course_activity_weekly_rows(rows), [{
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'interval_start': interval_start,
            'interval_end': interval_end,
            'created': created,
            'any': 300,
        }])


class InsightsSnowflakeServiceTests(SimpleTestCase):
    """Cover service orchestration without real Snowflake calls."""

    @patch('analytics_data_api.insights_snowflake.service.map_course_activity_weekly_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_course_activity_weekly_rows')
    def test_get_course_activity_weekly_calls_query_and_mapper(self, mock_get_rows, mock_map_rows):
        raw_rows = [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}]
        mapped_rows = [{'course_id': 'course-v1:edX+DemoX+Demo_Course', 'any': 300}]
        mock_get_rows.return_value = raw_rows
        mock_map_rows.return_value = mapped_rows
        start_date = datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2014, 1, 8, tzinfo=datetime.timezone.utc)

        self.assertEqual(
            get_course_activity_weekly(
                'course-v1:edX+DemoX+Demo_Course',
                start_date=start_date,
                end_date=end_date,
            ),
            mapped_rows,
        )

        mock_get_rows.assert_called_once_with(
            'course-v1:edX+DemoX+Demo_Course',
            start_date=start_date,
            end_date=end_date,
        )
        mock_map_rows.assert_called_once_with(raw_rows)


class InsightsSnowflakeToggleTests(SimpleTestCase):
    """Cover endpoint Waffle flag wrapper."""

    @patch('analytics_data_api.insights_snowflake.toggles.flag_is_active')
    def test_is_course_activity_snowflake_enabled_uses_endpoint_flag(self, mock_flag_is_active):
        request = Mock()
        mock_flag_is_active.return_value = True

        self.assertTrue(is_course_activity_snowflake_enabled(request))

        mock_flag_is_active.assert_called_once_with(request, COURSE_ACTIVITY_SNOWFLAKE_FLAG)
