from functools import reduce as functools_reduce

from django.db.models import Q
from django.http import Http404

from analytics_data_api.insights_snowflake.response_headers import InsightsDataSourceResponseMixin
from analytics_data_api.insights_snowflake.service import get_program_metadata
from analytics_data_api.insights_snowflake.toggles import is_insights_snowflake_enabled
from analytics_data_api.v0 import models, serializers
from analytics_data_api.v0.views import APIListView


class ProgramsView(InsightsDataSourceResponseMixin, APIListView):
    """
    Returns metadata information for programs.

    **Example Request**

        GET /api/v0/course_programs/?program_ids={program_id},{program_id}

    **Response Values**

        Returns metadata for every program:

            * program_id: The ID of the program for which data is returned.
            * program_type: The type of the program
            * program_title: The title of the program
            * created: The date the metadata was computed.

    **Parameters**

        Results can be filtered to the program IDs specified or limited to the fields.

        program_ids -- The comma-separated program identifiers for which metadata is requested.
            Default is to return all programs.
        fields -- The comma-separated fields to return in the response.
            For example, 'program_id,created'.  Default is to return all fields.
        exclude -- The comma-separated fields to exclude in the response.
            For example, 'program_id,created'.  Default is to not exclude any fields.
    """
    serializer_class = serializers.CourseProgramMetadataSerializer
    model = models.CourseProgramMetadata
    model_id_field = 'program_id'
    ids_param = 'program_ids'
    program_meta_fields = ['program_type', 'program_title']

    def base_field_dict(self, item_id):
        """Default program with id, empty metadata, and empty courses array."""
        program = super().base_field_dict(item_id)
        program.update({
            'program_type': '',
            'program_title': '',
            'created': None,
            'course_ids': [],
        })
        return program

    def update_field_dict_from_model(self, model, base_field_dict=None, field_list=None):
        field_dict = super().update_field_dict_from_model(model, base_field_dict=base_field_dict,
                                                          field_list=self.program_meta_fields)
        field_dict['course_ids'].append(model.course_id)

        # treat the most recent as the authoritative created date -- should be all the same
        field_dict['created'] = max(model.created, field_dict['created']) if field_dict['created'] else model.created

        return field_dict

    def get_query(self):
        return functools_reduce(lambda q, item_id: q | Q(program_id=item_id), self.ids, Q())

    def get_snowflake_queryset(self):
        """Return Snowflake-backed program metadata."""
        data = get_program_metadata(program_ids=self.ids)
        if data:
            return data
        raise Http404

    def get_queryset(self):
        if is_insights_snowflake_enabled(self.request):
            self.set_insights_data_source_snowflake()
            return self.get_snowflake_queryset()

        self.set_insights_data_source_aurora()
        return super().get_queryset()
