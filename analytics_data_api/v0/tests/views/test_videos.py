import datetime
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone
from django_dynamic_fixture import G

from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0 import models
from analyticsdataserver.tests.utils import TestCaseWithAuthentication


@set_databases
class VideoTimelineTests(TestCaseWithAuthentication):
    def _get_data(self, video_id=None):
        return self.authenticated_get(f'/api/v0/videos/{video_id}/timeline')

    def test_get(self):
        # add a blank row, which shouldn't be included in results
        G(models.VideoTimeline)

        video_id = 'v1d30'
        created = timezone.now()
        G(models.VideoTimeline, pipeline_video_id=video_id, segment=0, num_users=10,
          num_views=50, created=created)
        G(models.VideoTimeline, pipeline_video_id=video_id, segment=1, num_users=1,
          num_views=1234, created=created)

        alt_video_id = 'altv1d30'
        alt_created = created + datetime.timedelta(seconds=17)
        G(models.VideoTimeline, pipeline_video_id=alt_video_id, segment=0, num_users=10231,
          num_views=834828, created=alt_created)

        expected = [
            {
                'segment': 0,
                'num_users': 10,
                'num_views': 50,
                'created': created.strftime(settings.DATETIME_FORMAT)
            },
            {
                'segment': 1,
                'num_users': 1,
                'num_views': 1234,
                'created': created.strftime(settings.DATETIME_FORMAT)
            }
        ]
        response = self._get_data(video_id)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data, expected)

        expected = [
            {
                'segment': 0,
                'num_users': 10231,
                'num_views': 834828,
                'created': alt_created.strftime(settings.DATETIME_FORMAT)
            }
        ]
        response = self._get_data(alt_video_id)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data, expected)

    def test_get_uses_aurora_when_global_snowflake_flag_disabled(self):
        video_id = 'v1d30'
        created = timezone.now()
        G(models.VideoTimeline, pipeline_video_id=video_id, segment=0, num_users=10,
          num_views=50, created=created)

        with patch('analytics_data_api.v0.views.videos.is_insights_snowflake_enabled', return_value=False), \
                patch('analytics_data_api.v0.views.videos.get_video_timeline') as mock_get_timeline:
            response = self.authenticated_get(f'/api/v1/videos/{video_id}/timeline/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Insights-Data-Source'], 'aurora')
        mock_get_timeline.assert_not_called()

    def test_get_uses_snowflake_service_when_global_flag_enabled(self):
        video_id = 'v1d30'
        created = timezone.now()
        snowflake_data = [{
            'segment': 0,
            'num_users': 10,
            'num_views': 50,
            'created': created,
        }]
        expected = [{
            'segment': 0,
            'num_users': 10,
            'num_views': 50,
            'created': created.strftime(settings.DATETIME_FORMAT),
        }]

        with patch('analytics_data_api.v0.views.videos.is_insights_snowflake_enabled', return_value=True), \
                patch(
                    'analytics_data_api.v0.views.videos.get_video_timeline',
                    return_value=snowflake_data,
                ) as mock_get_timeline:
            response = self.authenticated_get(f'/api/v1/videos/{video_id}/timeline/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)
        self.assertEqual(response['X-Insights-Data-Source'], 'snowflake')
        mock_get_timeline.assert_called_once_with(video_id)

    def test_get_returns_404_when_snowflake_service_returns_no_data(self):
        video_id = 'v1d30'

        with patch('analytics_data_api.v0.views.videos.is_insights_snowflake_enabled', return_value=True), \
                patch(
                    'analytics_data_api.v0.views.videos.get_video_timeline',
                    return_value=[],
                ) as mock_get_timeline:
            response = self.authenticated_get(f'/api/v1/videos/{video_id}/timeline/')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['X-Insights-Data-Source'], 'snowflake')
        mock_get_timeline.assert_called_once_with(video_id)

    def test_get_404(self):
        response = self._get_data('no_id')
        self.assertEqual(response.status_code, 404)
