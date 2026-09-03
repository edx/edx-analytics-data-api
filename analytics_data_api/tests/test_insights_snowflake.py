"""Tests for Snowflake-backed Insights endpoint helpers."""

import datetime
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from rest_framework.response import Response

from analytics_data_api.constants import country, enrollment_modes, genders
from analytics_data_api.insights_snowflake.client import fetch_all, get_qualified_table_name
from analytics_data_api.insights_snowflake.mappers.activity import map_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.mappers.course_summaries import map_course_summary_rows
from analytics_data_api.insights_snowflake.mappers.enrollment import (
    map_course_enrollment_daily_rows,
    map_course_enrollment_education_rows,
    map_course_enrollment_gender_rows,
    map_course_enrollment_location_rows,
    map_course_enrollment_mode_rows,
)
from analytics_data_api.insights_snowflake.mappers.programs import map_program_metadata_rows
from analytics_data_api.insights_snowflake.queries.activity import get_course_activity_weekly_rows
from analytics_data_api.insights_snowflake.queries.course_summaries import (
    COURSE_ENROLLMENT_DAILY_TABLE,
    COURSE_META_SUMMARY_ENROLLMENT_TABLE,
    COURSE_PROGRAM_METADATA_TABLE as COURSE_SUMMARY_PROGRAM_METADATA_TABLE,
    get_course_recent_enrollment_rows,
    get_course_summary_program_rows,
    get_course_summary_rows,
)
from analytics_data_api.insights_snowflake.queries.enrollment import (
    COURSE_ENROLLMENT_EDUCATION_LEVEL_CURRENT_TABLE,
    COURSE_ENROLLMENT_GENDER_DAILY_TABLE,
    COURSE_ENROLLMENT_LOCATION_CURRENT_TABLE,
    get_course_enrollment_daily_rows,
    get_course_enrollment_education_rows,
    get_course_enrollment_gender_rows,
    get_course_enrollment_location_rows,
    get_course_enrollment_mode_rows,
)
from analytics_data_api.insights_snowflake.queries.programs import (
    COURSE_PROGRAM_METADATA_TABLE,
    get_program_metadata_rows,
)
from analytics_data_api.insights_snowflake.response_headers import (
    DATA_SOURCE_HEADER,
    DATA_SOURCE_SNOWFLAKE,
    InsightsDataSourceResponseMixin,
)
from analytics_data_api.insights_snowflake.service import (
    get_course_activity_weekly,
    get_course_enrollment,
    get_course_enrollment_education,
    get_course_enrollment_gender,
    get_course_enrollment_location,
    get_course_enrollment_mode,
    get_course_summaries,
    get_program_metadata,
)
from analytics_data_api.insights_snowflake.toggles import (
    COURSE_ACTIVITY_SNOWFLAKE_FLAG,
    INSIGHTS_SNOWFLAKE_FLAG,
    is_course_activity_snowflake_enabled,
    is_insights_snowflake_enabled,
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


class InsightsSnowflakeEnrollmentQueryTests(SimpleTestCase):
    """Cover enrollment query construction with mocked Snowflake execution."""

    @patch('analytics_data_api.insights_snowflake.queries.enrollment.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.enrollment.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_ENROLLMENT_DAILY')
    )
    def test_get_course_enrollment_daily_rows_uses_latest_date_query_without_dates(self, mock_fetch_all):
        mock_fetch_all.return_value = [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}]

        rows = get_course_enrollment_daily_rows('course-v1:edX+DemoX+Demo_Course')

        self.assertEqual(rows, [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}])
        sql, params = mock_fetch_all.call_args[0]
        self.assertIn('SELECT MAX("DATE")', sql)
        self.assertEqual(params, {'course_id': 'course-v1:edX+DemoX+Demo_Course'})

    @patch('analytics_data_api.insights_snowflake.queries.enrollment.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.enrollment.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_ENROLLMENT_MODE_DAILY')
    )
    def test_get_course_enrollment_mode_rows_uses_date_range_query_with_dates(self, mock_fetch_all):
        start_date = datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2014, 1, 8, tzinfo=datetime.timezone.utc)

        get_course_enrollment_mode_rows(
            'course-v1:edX+DemoX+Demo_Course',
            start_date=start_date,
            end_date=end_date,
        )

        sql, params = mock_fetch_all.call_args[0]
        self.assertIn('"DATE" >= %(start_date)s', sql)
        self.assertIn('"DATE" < %(end_date)s', sql)
        self.assertEqual(params, {
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'start_date': start_date.date(),
            'end_date': end_date.date(),
        })

    @patch('analytics_data_api.insights_snowflake.queries.enrollment.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.enrollment.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_ENROLLMENT_DAILY')
    )
    def test_get_course_enrollment_daily_rows_accepts_date_objects(self, mock_fetch_all):
        start_date = datetime.date(2014, 1, 1)
        end_date = datetime.date(2014, 1, 8)

        get_course_enrollment_daily_rows(
            'course-v1:edX+DemoX+Demo_Course',
            start_date=start_date,
            end_date=end_date,
        )

        _sql, params = mock_fetch_all.call_args[0]
        self.assertEqual(params, {
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'start_date': start_date,
            'end_date': end_date,
        })

    @patch('analytics_data_api.insights_snowflake.queries.enrollment.fetch_all')
    @patch('analytics_data_api.insights_snowflake.queries.enrollment.get_qualified_table_name')
    def test_enrollment_query_functions_use_expected_tables(self, mock_get_table_name, _mock_fetch_all):
        mock_get_table_name.return_value = 'PROD.INSIGHTS.ENROLLMENT_TABLE'
        course_id = 'course-v1:edX+DemoX+Demo_Course'

        query_functions = [
            (get_course_enrollment_education_rows, COURSE_ENROLLMENT_EDUCATION_LEVEL_CURRENT_TABLE, 'education_level'),
            (get_course_enrollment_gender_rows, COURSE_ENROLLMENT_GENDER_DAILY_TABLE, 'gender'),
            (get_course_enrollment_location_rows, COURSE_ENROLLMENT_LOCATION_CURRENT_TABLE, 'country_code'),
        ]

        for query_function, table, expected_column in query_functions:
            mock_get_table_name.reset_mock()
            _mock_fetch_all.reset_mock()

            query_function(course_id)

            mock_get_table_name.assert_called_once_with(table)
            sql, params = _mock_fetch_all.call_args[0]
            self.assertIn(expected_column, sql)
            self.assertEqual(params, {'course_id': course_id})


class InsightsSnowflakeCourseSummaryQueryTests(SimpleTestCase):
    """Cover course summary query construction with mocked Snowflake execution."""

    @patch('analytics_data_api.insights_snowflake.queries.course_summaries.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.course_summaries.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_META_SUMMARY_ENROLLMENT')
    )
    def test_get_course_summary_rows_uses_expected_table_without_ids(self, mock_fetch_all):
        mock_fetch_all.return_value = [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}]

        rows = get_course_summary_rows()

        self.assertEqual(rows, [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}])
        sql, params = mock_fetch_all.call_args[0]
        self.assertIn('FROM PROD.INSIGHTS.COURSE_META_SUMMARY_ENROLLMENT', sql)
        self.assertNotIn('WHERE course_id IN', sql)
        self.assertEqual(params, {})

    @patch('analytics_data_api.insights_snowflake.queries.course_summaries.fetch_all')
    @patch('analytics_data_api.insights_snowflake.queries.course_summaries.get_qualified_table_name')
    def test_course_summary_query_functions_use_expected_tables(self, mock_get_table_name, _mock_fetch_all):
        mock_get_table_name.return_value = 'PROD.INSIGHTS.COURSE_SUMMARY_TABLE'
        course_ids = ['course-v1:edX+DemoX+Demo_Course', 'course-v1:edX+DemoX+Demo_2014']

        query_functions = [
            (get_course_summary_rows, COURSE_META_SUMMARY_ENROLLMENT_TABLE),
            (get_course_summary_program_rows, COURSE_SUMMARY_PROGRAM_METADATA_TABLE),
        ]

        for query_function, table in query_functions:
            mock_get_table_name.reset_mock()
            _mock_fetch_all.reset_mock()

            query_function(course_ids=course_ids)

            mock_get_table_name.assert_called_once_with(table)
            sql, params = _mock_fetch_all.call_args[0]
            self.assertIn('course_id IN (%(course_id_0)s, %(course_id_1)s)', sql)
            self.assertEqual(params, {
                'course_id_0': course_ids[0],
                'course_id_1': course_ids[1],
            })

    @patch('analytics_data_api.insights_snowflake.queries.course_summaries.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.course_summaries.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_ENROLLMENT_DAILY')
    )
    def test_get_course_recent_enrollment_rows_accepts_datetime_recent_date(self, mock_fetch_all):
        recent_date = datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc)

        get_course_recent_enrollment_rows(
            course_ids=['course-v1:edX+DemoX+Demo_Course'],
            recent_date=recent_date,
        )

        sql, params = mock_fetch_all.call_args[0]
        self.assertIn('FROM PROD.INSIGHTS.COURSE_ENROLLMENT_DAILY', sql)
        self.assertIn('AND course_id IN (%(course_id_0)s)', sql)
        self.assertEqual(params, {
            'recent_date': recent_date.date(),
            'course_id_0': 'course-v1:edX+DemoX+Demo_Course',
        })

    @patch('analytics_data_api.insights_snowflake.queries.course_summaries.fetch_all')
    @patch('analytics_data_api.insights_snowflake.queries.course_summaries.get_qualified_table_name')
    def test_get_course_recent_enrollment_rows_uses_expected_table(self, mock_get_table_name, _mock_fetch_all):
        mock_get_table_name.return_value = 'PROD.INSIGHTS.COURSE_ENROLLMENT_DAILY'
        recent_date = datetime.date(2014, 1, 1)

        get_course_recent_enrollment_rows(recent_date=recent_date)

        mock_get_table_name.assert_called_once_with(COURSE_ENROLLMENT_DAILY_TABLE)
        sql, params = _mock_fetch_all.call_args[0]
        self.assertNotIn('AND course_id IN', sql)
        self.assertEqual(params, {'recent_date': recent_date})


class InsightsSnowflakeProgramQueryTests(SimpleTestCase):
    """Cover program metadata query construction with mocked Snowflake execution."""

    @patch('analytics_data_api.insights_snowflake.queries.programs.fetch_all')
    @patch(
        'analytics_data_api.insights_snowflake.queries.programs.get_qualified_table_name',
        Mock(return_value='PROD.INSIGHTS.COURSE_PROGRAM_METADATA')
    )
    def test_get_program_metadata_rows_uses_expected_table_without_ids(self, mock_fetch_all):
        mock_fetch_all.return_value = [{'program_id': 'program-1'}]

        rows = get_program_metadata_rows()

        self.assertEqual(rows, [{'program_id': 'program-1'}])
        sql, params = mock_fetch_all.call_args[0]
        self.assertIn('FROM PROD.INSIGHTS.COURSE_PROGRAM_METADATA', sql)
        self.assertNotIn('WHERE program_id IN', sql)
        self.assertEqual(params, {})

    @patch('analytics_data_api.insights_snowflake.queries.programs.fetch_all')
    @patch('analytics_data_api.insights_snowflake.queries.programs.get_qualified_table_name')
    def test_get_program_metadata_rows_filters_program_ids(self, mock_get_table_name, _mock_fetch_all):
        mock_get_table_name.return_value = 'PROD.INSIGHTS.COURSE_PROGRAM_METADATA'
        program_ids = ['program-1', 'program-2']

        get_program_metadata_rows(program_ids=program_ids)

        mock_get_table_name.assert_called_once_with(COURSE_PROGRAM_METADATA_TABLE)
        sql, params = _mock_fetch_all.call_args[0]
        self.assertIn('WHERE program_id IN (%(program_id_0)s, %(program_id_1)s)', sql)
        self.assertEqual(params, {
            'program_id_0': program_ids[0],
            'program_id_1': program_ids[1],
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


class InsightsSnowflakeEnrollmentMapperTests(SimpleTestCase):
    """Cover Snowflake enrollment row mapping into the existing API shapes."""

    def test_map_course_enrollment_daily_rows_accepts_uppercase_snowflake_keys(self):
        date = datetime.date(2014, 1, 1)
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        rows = [{
            'COURSE_ID': 'course-v1:edX+DemoX+Demo_Course',
            'DATE': date,
            'COUNT': 203,
            'CREATED': created,
        }]

        self.assertEqual(map_course_enrollment_daily_rows(rows), [{
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'date': date,
            'count': 203,
            'created': created,
        }])

    def test_map_course_enrollment_education_rows(self):
        date = datetime.date(2014, 1, 1)
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        rows = [{
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'date': date,
            'education_level': 'bachelors',
            'count': 25,
            'created': created,
        }]

        self.assertEqual(map_course_enrollment_education_rows(rows), [{
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'date': date,
            'education_level': 'bachelors',
            'count': 25,
            'created': created,
        }])

    def test_map_course_enrollment_mode_rows_pivots_modes(self):
        date = datetime.date(2014, 1, 1)
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        later_created = datetime.datetime(2014, 1, 3, tzinfo=datetime.timezone.utc)
        rows = [
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'mode': enrollment_modes.PROFESSIONAL_NO_ID,
                'count': 3,
                'cumulative_count': 7,
                'created': created,
            },
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'mode': enrollment_modes.PROFESSIONAL,
                'count': 4,
                'cumulative_count': 8,
                'created': later_created,
            },
        ]

        self.assertEqual(map_course_enrollment_mode_rows(rows), [{
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'date': date,
            'created': later_created,
            enrollment_modes.PROFESSIONAL: 7,
            'count': 7,
            'cumulative_count': 15,
        }])

    def test_map_course_enrollment_gender_rows_pivots_genders(self):
        date = datetime.date(2014, 1, 1)
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        rows = [
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'gender': 'f',
                'count': 3,
                'created': created,
            },
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'gender': None,
                'count': 4,
                'created': created,
            },
        ]

        self.assertEqual(map_course_enrollment_gender_rows(rows), [{
            'course_id': 'course-v1:edX+DemoX+Demo_Course',
            'date': date,
            'created': created,
            genders.MALE: 0,
            genders.FEMALE: 3,
            genders.OTHER: 0,
            genders.UNKNOWN: 4,
        }])

    def test_map_course_enrollment_location_rows_groups_unknown_countries(self):
        date = datetime.date(2014, 1, 1)
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        rows = [
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'country_code': '',
                'count': 3,
                'created': created,
            },
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'country_code': None,
                'count': 4,
                'created': created,
            },
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'country_code': 'US',
                'count': 5,
                'created': created,
            },
        ]

        mapped_rows = map_course_enrollment_location_rows(rows)

        self.assertEqual(len(mapped_rows), 2)
        self.assertEqual(mapped_rows[0].country.name, country.UNKNOWN_COUNTRY_CODE)
        self.assertEqual(mapped_rows[0].count, 7)
        self.assertEqual(mapped_rows[1].country.alpha2, 'US')
        self.assertEqual(mapped_rows[1].count, 5)

    def test_map_course_enrollment_location_rows_groups_unsorted_dates(self):
        date = datetime.date(2014, 1, 1)
        next_date = datetime.date(2014, 1, 2)
        created = datetime.datetime(2014, 1, 3, tzinfo=datetime.timezone.utc)
        rows = [
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'country_code': 'US',
                'count': 3,
                'created': created,
            },
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': next_date,
                'country_code': 'US',
                'count': 4,
                'created': created,
            },
            {
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'date': date,
                'country_code': 'US',
                'count': 5,
                'created': created,
            },
        ]

        mapped_rows = map_course_enrollment_location_rows(rows)

        self.assertEqual(len(mapped_rows), 2)
        self.assertEqual(mapped_rows[0].date, date)
        self.assertEqual(mapped_rows[0].count, 8)
        self.assertEqual(mapped_rows[1].date, next_date)
        self.assertEqual(mapped_rows[1].count, 4)


class InsightsSnowflakeProgramMapperTests(SimpleTestCase):
    """Cover Snowflake program rows mapping into the existing API shape."""

    def test_map_program_metadata_rows_groups_courses_and_accepts_uppercase_keys(self):
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        later_created = datetime.datetime(2014, 1, 3, tzinfo=datetime.timezone.utc)
        rows = [
            {
                'PROGRAM_ID': 'program-1',
                'PROGRAM_TYPE': 'Demo',
                'PROGRAM_TITLE': 'Test',
                'COURSE_ID': 'course-v1:edX+DemoX+Demo_2014',
                'CREATED': created,
            },
            {
                'PROGRAM_ID': 'program-1',
                'PROGRAM_TYPE': 'Demo',
                'PROGRAM_TITLE': 'Test',
                'COURSE_ID': 'course-v1:edX+DemoX+Demo_Course',
                'CREATED': later_created,
            },
        ]

        self.assertEqual(map_program_metadata_rows(rows), [{
            'program_id': 'program-1',
            'program_type': 'Demo',
            'program_title': 'Test',
            'created': later_created,
            'course_ids': [
                'course-v1:edX+DemoX+Demo_2014',
                'course-v1:edX+DemoX+Demo_Course',
            ],
        }])

    def test_map_program_metadata_rows_handles_null_sort_values(self):
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        rows = [
            {
                'program_id': 'program-1',
                'program_type': 'Demo',
                'program_title': 'Test',
                'course_id': 'course-v1:edX+DemoX+Demo_Course',
                'created': created,
            },
            {
                'program_id': 'program-1',
                'program_type': 'Demo',
                'program_title': 'Test',
                'course_id': None,
                'created': created,
            },
        ]

        self.assertEqual(map_program_metadata_rows(rows), [{
            'program_id': 'program-1',
            'program_type': 'Demo',
            'program_title': 'Test',
            'created': created,
            'course_ids': [
                None,
                'course-v1:edX+DemoX+Demo_Course',
            ],
        }])


class InsightsSnowflakeCourseSummaryMapperTests(SimpleTestCase):
    """Cover Snowflake course summary rows mapping into the existing API shape."""

    def test_map_course_summary_rows_merges_modes_programs_and_recent_counts(self):
        course_id = 'course-v1:edX+DemoX+Demo_Course'
        start_time = datetime.datetime(2016, 10, 11, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2016, 12, 18, tzinfo=datetime.timezone.utc)
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        later_created = datetime.datetime(2014, 1, 3, tzinfo=datetime.timezone.utc)
        summary_rows = [
            {
                'COURSE_ID': course_id,
                'CATALOG_COURSE_TITLE': 'Title',
                'CATALOG_COURSE': 'Catalog',
                'START_TIME': start_time,
                'END_TIME': end_time,
                'PACING_TYPE': 'instructor',
                'AVAILABILITY': 'Starting Soon',
                'ENROLLMENT_MODE': enrollment_modes.PROFESSIONAL_NO_ID,
                'COUNT': 3,
                'CUMULATIVE_COUNT': 7,
                'COUNT_CHANGE_7_DAYS': 1,
                'PASSING_USERS': None,
                'CREATED': created,
            },
            {
                'COURSE_ID': course_id,
                'CATALOG_COURSE_TITLE': 'Title',
                'CATALOG_COURSE': 'Catalog',
                'START_TIME': start_time,
                'END_TIME': end_time,
                'PACING_TYPE': 'instructor',
                'AVAILABILITY': 'Starting Soon',
                'ENROLLMENT_MODE': enrollment_modes.PROFESSIONAL,
                'COUNT': 4,
                'CUMULATIVE_COUNT': 8,
                'COUNT_CHANGE_7_DAYS': 2,
                'PASSING_USERS': 6,
                'CREATED': later_created,
            },
        ]
        program_rows = [{
            'course_id': course_id,
            'program_id': 'program-1',
        }]
        recent_rows = [{
            'course_id': course_id,
            'count': 2,
        }]

        mapped_rows = map_course_summary_rows(
            summary_rows,
            program_rows=program_rows,
            recent_rows=recent_rows,
            exclude=['passing_users'],
        )

        self.assertEqual(len(mapped_rows), 1)
        summary = mapped_rows[0]
        self.assertEqual(summary['course_id'], course_id)
        self.assertEqual(summary['availability'], 'Upcoming')
        self.assertEqual(summary['created'], later_created)
        self.assertEqual(summary['count'], 7)
        self.assertEqual(summary['cumulative_count'], 15)
        self.assertEqual(summary['count_change_7_days'], 3)
        self.assertEqual(summary['passing_users'], 6)
        self.assertEqual(summary['recent_count_change'], 5)
        self.assertEqual(summary['programs'], ['program-1'])
        self.assertNotIn(enrollment_modes.PROFESSIONAL_NO_ID, summary['enrollment_modes'])
        self.assertEqual(summary['enrollment_modes'][enrollment_modes.PROFESSIONAL]['count'], 7)
        self.assertNotIn('passing_users', summary['enrollment_modes'][enrollment_modes.PROFESSIONAL])

    def test_map_course_summary_rows_handles_null_sort_values(self):
        course_id = 'course-v1:edX+DemoX+Demo_Course'
        start_time = datetime.datetime(2016, 10, 11, tzinfo=datetime.timezone.utc)
        end_time = datetime.datetime(2016, 12, 18, tzinfo=datetime.timezone.utc)
        created = datetime.datetime(2014, 1, 2, tzinfo=datetime.timezone.utc)
        summary_rows = [
            {
                'course_id': course_id,
                'catalog_course_title': 'Title',
                'catalog_course': 'Catalog',
                'start_time': start_time,
                'end_time': end_time,
                'pacing_type': 'instructor',
                'availability': 'Current',
                'enrollment_mode': enrollment_modes.PROFESSIONAL,
                'count': 4,
                'cumulative_count': 8,
                'count_change_7_days': 2,
                'passing_users': 6,
                'created': created,
            },
            {
                'course_id': course_id,
                'catalog_course_title': 'Title',
                'catalog_course': 'Catalog',
                'start_time': start_time,
                'end_time': end_time,
                'pacing_type': 'instructor',
                'availability': 'Current',
                'enrollment_mode': None,
                'count': 3,
                'cumulative_count': 7,
                'count_change_7_days': 1,
                'passing_users': 0,
                'created': created,
            },
        ]

        mapped_rows = map_course_summary_rows(summary_rows)

        self.assertEqual(len(mapped_rows), 1)
        self.assertEqual(mapped_rows[0]['count'], 7)
        self.assertEqual(mapped_rows[0]['enrollment_modes'][enrollment_modes.PROFESSIONAL]['count'], 4)


class InsightsSnowflakeServiceTests(SimpleTestCase):
    """Cover service orchestration without real Snowflake calls."""

    def assertServiceCallsQueryAndMapper(self, service_function, query_path, mapper_path):
        raw_rows = [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}]
        mapped_rows = [{'course_id': 'course-v1:edX+DemoX+Demo_Course', 'count': 203}]
        start_date = datetime.datetime(2014, 1, 1, tzinfo=datetime.timezone.utc)
        end_date = datetime.datetime(2014, 1, 8, tzinfo=datetime.timezone.utc)

        with patch(query_path) as mock_get_rows, patch(mapper_path) as mock_map_rows:
            mock_get_rows.return_value = raw_rows
            mock_map_rows.return_value = mapped_rows

            self.assertEqual(
                service_function(
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

    def test_get_course_enrollment_calls_query_and_mapper(self):
        self.assertServiceCallsQueryAndMapper(
            get_course_enrollment,
            'analytics_data_api.insights_snowflake.service.get_course_enrollment_daily_rows',
            'analytics_data_api.insights_snowflake.service.map_course_enrollment_daily_rows',
        )

    def test_get_course_enrollment_mode_calls_query_and_mapper(self):
        self.assertServiceCallsQueryAndMapper(
            get_course_enrollment_mode,
            'analytics_data_api.insights_snowflake.service.get_course_enrollment_mode_rows',
            'analytics_data_api.insights_snowflake.service.map_course_enrollment_mode_rows',
        )

    def test_get_course_enrollment_education_calls_query_and_mapper(self):
        self.assertServiceCallsQueryAndMapper(
            get_course_enrollment_education,
            'analytics_data_api.insights_snowflake.service.get_course_enrollment_education_rows',
            'analytics_data_api.insights_snowflake.service.map_course_enrollment_education_rows',
        )

    def test_get_course_enrollment_gender_calls_query_and_mapper(self):
        self.assertServiceCallsQueryAndMapper(
            get_course_enrollment_gender,
            'analytics_data_api.insights_snowflake.service.get_course_enrollment_gender_rows',
            'analytics_data_api.insights_snowflake.service.map_course_enrollment_gender_rows',
        )

    def test_get_course_enrollment_location_calls_query_and_mapper(self):
        self.assertServiceCallsQueryAndMapper(
            get_course_enrollment_location,
            'analytics_data_api.insights_snowflake.service.get_course_enrollment_location_rows',
            'analytics_data_api.insights_snowflake.service.map_course_enrollment_location_rows',
        )

    @patch('analytics_data_api.insights_snowflake.service.map_program_metadata_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_program_metadata_rows')
    def test_get_program_metadata_calls_query_and_mapper(self, mock_get_rows, mock_map_rows):
        raw_rows = [{'program_id': 'program-1'}]
        mapped_rows = [{'program_id': 'program-1', 'course_ids': ['course-v1:edX+DemoX+Demo_Course']}]
        mock_get_rows.return_value = raw_rows
        mock_map_rows.return_value = mapped_rows

        self.assertEqual(get_program_metadata(program_ids=['program-1']), mapped_rows)

        mock_get_rows.assert_called_once_with(program_ids=['program-1'])
        mock_map_rows.assert_called_once_with(raw_rows)

    @patch('analytics_data_api.insights_snowflake.service.map_course_summary_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_course_recent_enrollment_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_course_summary_program_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_course_summary_rows')
    def test_get_course_summaries_calls_required_queries_and_mapper(
            self,
            mock_get_summary_rows,
            mock_get_program_rows,
            mock_get_recent_rows,
            mock_map_rows,
    ):
        course_ids = ['course-v1:edX+DemoX+Demo_Course']
        recent_date = datetime.date(2014, 1, 1)
        summary_rows = [{'course_id': course_ids[0]}]
        program_rows = [{'course_id': course_ids[0], 'program_id': 'program-1'}]
        recent_rows = [{'course_id': course_ids[0], 'count': 3}]
        mapped_rows = [{'course_id': course_ids[0], 'count': 4}]
        mock_get_summary_rows.return_value = summary_rows
        mock_get_program_rows.return_value = program_rows
        mock_get_recent_rows.return_value = recent_rows
        mock_map_rows.return_value = mapped_rows

        self.assertEqual(
            get_course_summaries(
                course_ids=course_ids,
                include_programs=True,
                recent_date=recent_date,
                exclude=['created'],
            ),
            mapped_rows,
        )

        mock_get_summary_rows.assert_called_once_with(course_ids=course_ids)
        mock_get_program_rows.assert_called_once_with(course_ids=course_ids)
        mock_get_recent_rows.assert_called_once_with(course_ids=course_ids, recent_date=recent_date)
        mock_map_rows.assert_called_once_with(
            summary_rows,
            program_rows=program_rows,
            recent_rows=recent_rows,
            exclude=['created'],
        )

    @patch('analytics_data_api.insights_snowflake.service.map_course_summary_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_course_recent_enrollment_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_course_summary_program_rows')
    @patch('analytics_data_api.insights_snowflake.service.get_course_summary_rows')
    def test_get_course_summaries_skips_optional_queries(
            self,
            mock_get_summary_rows,
            mock_get_program_rows,
            mock_get_recent_rows,
            mock_map_rows,
    ):
        summary_rows = [{'course_id': 'course-v1:edX+DemoX+Demo_Course'}]
        mapped_rows = [{'course_id': 'course-v1:edX+DemoX+Demo_Course', 'count': 4}]
        mock_get_summary_rows.return_value = summary_rows
        mock_map_rows.return_value = mapped_rows

        self.assertEqual(get_course_summaries(), mapped_rows)

        mock_get_summary_rows.assert_called_once_with(course_ids=None)
        mock_get_program_rows.assert_not_called()
        mock_get_recent_rows.assert_not_called()
        mock_map_rows.assert_called_once_with(summary_rows, program_rows=None, recent_rows=None, exclude=None)


class BaseTestView:
    """Small base class for testing response mixin behavior."""

    def finalize_response(self, _request, response, *_args, **_kwargs):
        return response


class InsightsDataSourceTestView(InsightsDataSourceResponseMixin, BaseTestView):
    """Test view using the Snowflake data source response mixin."""


class InsightsSnowflakeResponseHeaderTests(SimpleTestCase):
    """Cover shared response header helpers."""

    def test_finalize_response_adds_data_source_header(self):
        view = InsightsDataSourceTestView()
        view.set_insights_data_source_snowflake()

        response = view.finalize_response(Mock(), Response({}))

        self.assertEqual(response[DATA_SOURCE_HEADER], DATA_SOURCE_SNOWFLAKE)

    def test_finalize_response_skips_header_when_source_is_not_set(self):
        view = InsightsDataSourceTestView()

        response = view.finalize_response(Mock(), Response({}))

        self.assertNotIn(DATA_SOURCE_HEADER, response)


class InsightsSnowflakeToggleTests(SimpleTestCase):
    """Cover endpoint Waffle flag wrapper."""

    @patch('analytics_data_api.insights_snowflake.toggles.flag_is_active')
    def test_is_insights_snowflake_enabled_uses_global_flag(self, mock_flag_is_active):
        request = Mock()
        mock_flag_is_active.return_value = True

        self.assertTrue(is_insights_snowflake_enabled(request))

        mock_flag_is_active.assert_called_once_with(request, INSIGHTS_SNOWFLAKE_FLAG)

    @patch('analytics_data_api.insights_snowflake.toggles.flag_is_active')
    def test_is_course_activity_snowflake_enabled_uses_global_flag(self, mock_flag_is_active):
        request = Mock()
        mock_flag_is_active.return_value = True

        self.assertTrue(is_course_activity_snowflake_enabled(request))

        mock_flag_is_active.assert_called_once_with(request, INSIGHTS_SNOWFLAKE_FLAG)

    @patch('analytics_data_api.insights_snowflake.toggles.flag_is_active')
    def test_is_course_activity_snowflake_enabled_uses_endpoint_flag(self, mock_flag_is_active):
        request = Mock()
        mock_flag_is_active.side_effect = [False, True]

        self.assertTrue(is_course_activity_snowflake_enabled(request))

        self.assertEqual(mock_flag_is_active.call_count, 2)
        self.assertEqual(mock_flag_is_active.call_args_list[0].args, (request, INSIGHTS_SNOWFLAKE_FLAG))
        self.assertEqual(mock_flag_is_active.call_args_list[1].args, (request, COURSE_ACTIVITY_SNOWFLAKE_FLAG))

    @patch('analytics_data_api.insights_snowflake.toggles.flag_is_active')
    def test_is_course_activity_snowflake_enabled_returns_false_when_flags_disabled(self, mock_flag_is_active):
        request = Mock()
        mock_flag_is_active.return_value = False

        self.assertFalse(is_course_activity_snowflake_enabled(request))

        self.assertEqual(mock_flag_is_active.call_count, 2)
        self.assertEqual(mock_flag_is_active.call_args_list[0].args, (request, INSIGHTS_SNOWFLAKE_FLAG))
        self.assertEqual(mock_flag_is_active.call_args_list[1].args, (request, COURSE_ACTIVITY_SNOWFLAKE_FLAG))
