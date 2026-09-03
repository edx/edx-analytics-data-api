"""
API methods for module level data.
"""

from django.http import Http404
from rest_framework import generics

from analytics_data_api.insights_snowflake.response_headers import InsightsDataSourceResponseMixin
from analytics_data_api.insights_snowflake.service import get_video_timeline
from analytics_data_api.insights_snowflake.toggles import is_insights_snowflake_enabled
from analytics_data_api.v0.models import VideoTimeline
from analytics_data_api.v0.serializers import VideoTimelineSerializer
from analytics_data_api.v0.views.utils import raise_404_if_none


class VideoTimelineView(InsightsDataSourceResponseMixin, generics.ListAPIView):
    """
    Get the counts of users and views for a video.

    **Example Request**

        GET /api/v0/videos/{video_id}/timeline/

    **Response Values**

        Returns viewing data for each segment of a video.  For each segment,
        the collection contains the following data.

            * segment: The order of the segment in the video timeline.
            * num_users: The number of unique users who viewed this segment.
            * num_views: The number of views for this segment.
            * created: The date the segment data was computed.
    """

    serializer_class = VideoTimelineSerializer
    allow_empty = False

    def get_snowflake_queryset(self):
        """Return Snowflake-backed timeline data for this video."""
        video_id = self.kwargs.get('video_id')
        data = get_video_timeline(video_id)
        if data:
            return data
        raise Http404

    @raise_404_if_none
    def get_queryset(self):
        """Select the view count for a specific module"""
        if is_insights_snowflake_enabled(self.request):
            self.set_insights_data_source_snowflake()
            return self.get_snowflake_queryset()

        self.set_insights_data_source_aurora()
        video_id = self.kwargs.get('video_id')
        return VideoTimeline.objects.filter(pipeline_video_id=video_id)
