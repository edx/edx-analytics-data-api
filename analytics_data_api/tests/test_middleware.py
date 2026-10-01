from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from analytics_data_api.middleware import RequestVersionMiddleware as AnalyticsRequestVersionMiddleware
from analytics_data_api.middleware import thread_data
from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0.tests.views import CourseSamples
from analyticsdataserver.tests.utils import TestCaseWithAuthentication


@set_databases
class RequestVersionMiddleware(TestCaseWithAuthentication):
    def test_request_version_middleware_v1(self):
        self.authenticated_get('/api/v1/courses/{}/activity'.format(
            CourseSamples.course_ids[0]))

        self.assertEqual(thread_data.analyticsapi_database, getattr(settings, 'ANALYTICS_DATABASE_V1'))

    @override_settings(ANALYTICS_DATABASE_V1=None)
    def test_request_version_middleware_v1_no_setting(self):
        self.authenticated_get('/api/v1/courses/{}/activity'.format(
            CourseSamples.course_ids[0]))

        self.assertEqual(thread_data.analyticsapi_database, getattr(settings, 'ANALYTICS_DATABASE_V1'))

    def test_request_version_middleware_v0(self):
        self.authenticated_get('/api/v0/courses/{}/activity'.format(
            CourseSamples.course_ids[0]))

        self.assertEqual("analytics", getattr(thread_data, 'analyticsapi_database'))


class RequestVersionMiddlewareTracingTests(SimpleTestCase):
    @override_settings(ANALYTICS_DATABASE='analytics', ANALYTICS_DATABASE_V1='analytics_v1')
    @patch('analytics_data_api.middleware.set_current_span_tags')
    def test_request_version_middleware_tags_v1(self, mock_set_current_span_tags):
        request = SimpleNamespace(path='/api/v1/courses/course/activity')
        response = object()
        middleware = AnalyticsRequestVersionMiddleware(lambda _request: response)

        self.assertIs(middleware(request), response)
        mock_set_current_span_tags.assert_called_once_with(**{'insights.api_version': 'v1'})

    @override_settings(ANALYTICS_DATABASE='analytics', ANALYTICS_DATABASE_V1='analytics_v1')
    @patch('analytics_data_api.middleware.set_current_span_tags')
    def test_request_version_middleware_tags_v0(self, mock_set_current_span_tags):
        request = SimpleNamespace(path='/api/v0/courses/course/activity')
        response = object()
        middleware = AnalyticsRequestVersionMiddleware(lambda _request: response)

        self.assertIs(middleware(request), response)
        mock_set_current_span_tags.assert_called_once_with(**{'insights.api_version': 'v0'})
