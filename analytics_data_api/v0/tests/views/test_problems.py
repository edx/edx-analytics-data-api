# NOTE: Full URLs are used throughout these tests to ensure that the API contract is fulfilled. The URLs should *not*
# change for versions greater than 1.0.0. Tests target a specific version of the API, additional tests should be added
# for subsequent versions if there are breaking changes introduced in those versions.

# pylint: disable=no-member,no-value-for-parameter

import json
from unittest.mock import patch

from django.conf import settings
from django_dynamic_fixture import G

from analytics_data_api.middleware import thread_data
from analytics_data_api.tests.test_utils import set_databases
from analytics_data_api.v0 import models
from analytics_data_api.v0.serializers import (
    GradeDistributionSerializer,
    ProblemFirstLastResponseAnswerDistributionSerializer,
    SequentialOpenDistributionSerializer,
)
from analyticsdataserver.tests.utils import TestCaseWithAuthentication


@set_databases
class AnswerDistributionTests(TestCaseWithAuthentication):
    path = '/answer_distribution/'
    maxDiff = None

    def tearDown(self):
        thread_data.analyticsapi_database = getattr(settings, 'ANALYTICS_DATABASE', 'analytics')
        super().tearDown()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.course_id = "org/num/run"
        cls.module_id1 = "i4x://org/num/run/problem/RANDOMNUMBER"
        cls.module_id2 = "i4x://org/num/run/problem/OTHERRANDOM"
        cls.part_id = "i4x-org-num-run-problem-RANDOMNUMBER_2_1"
        cls.correct = True
        cls.value_id1 = '3'
        cls.value_id2 = '4'
        cls.answer_value = '3'
        cls.problem_display_name = 'Test Problem'
        cls.question_text = 'Question Text'

        cls.ad1 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id1,
            part_id=cls.part_id,
            correct=cls.correct,
            value_id=cls.value_id1,
            answer_value=cls.answer_value,
            problem_display_name=cls.problem_display_name,
            question_text=cls.question_text,
            variant=123,
            first_response_count=1,
            last_response_count=3,
        )
        cls.ad2 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id1,
            part_id=cls.part_id,
            correct=cls.correct,
            value_id=cls.value_id1,
            answer_value=cls.answer_value,
            problem_display_name=cls.problem_display_name,
            question_text=cls.question_text,
            variant=345,
            first_response_count=0,
            last_response_count=2,
        )
        cls.ad3 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id1,
            part_id=cls.part_id,
        )
        cls.ad4 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id2,
            part_id=cls.part_id,
            value_id=cls.value_id1,
            correct=True,
        )
        cls.ad5 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id2,
            part_id=cls.part_id,
            value_id=cls.value_id2,
            correct=True
        )
        cls.ad6 = G(
            models.ProblemFirstLastResponseAnswerDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id2,
            part_id=cls.part_id,
            value_id=cls.value_id1,
            correct=False,
        )

    def test_nonconsolidated_get(self):
        """ Verify that answers which should not be consolidated are not. """
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id2, self.path))
        self.assertEqual(response.status_code, 200)

        expected_data = models.ProblemFirstLastResponseAnswerDistribution.objects.filter(module_id=self.module_id2)
        expected_data = [ProblemFirstLastResponseAnswerDistributionSerializer(answer).data for answer in expected_data]

        for answer in expected_data:
            answer['consolidated_variant'] = False

        response.data = {json.dumps(answer) for answer in response.data}
        expected_data = {json.dumps(answer) for answer in expected_data}

        self.assertEqual(response.data, expected_data)

    def test_consolidated_get(self):
        """ Verify that valid consolidation does occur. """
        response = self.authenticated_get(
            f'/api/v0/problems/{self.module_id1}{self.path}')
        self.assertEqual(response.status_code, 200)

        expected_data = [self.ad1, self.ad3]

        expected_data[0].first_response_count += self.ad2.first_response_count
        expected_data[0].last_response_count += self.ad2.last_response_count

        expected_data = [ProblemFirstLastResponseAnswerDistributionSerializer(answer).data for answer in expected_data]

        expected_data[0]['variant'] = None
        expected_data[0]['consolidated_variant'] = True

        expected_data[1]['consolidated_variant'] = False

        response.data = [json.dumps(answer) for answer in response.data]
        expected_data = [json.dumps(answer) for answer in expected_data]

        self.assertEqual(set(response.data), set(expected_data))

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEqual(response.status_code, 404)

    def test_get_uses_aurora_when_global_snowflake_flag_disabled(self):
        with patch('analytics_data_api.v0.views.problems.is_insights_snowflake_enabled', return_value=False):
            with patch(
                    'analytics_data_api.v0.views.problems.get_problem_answer_distribution',
            ) as mock_get_answer_distribution:
                response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id2, self.path))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Insights-Data-Source'], 'aurora')
        mock_get_answer_distribution.assert_not_called()

    def test_get_uses_snowflake_service_when_global_flag_enabled(self):
        created = self.ad1.created
        snowflake_data = [
            models.ProblemFirstLastResponseAnswerDistribution(
                course_id=self.course_id,
                module_id=self.module_id1,
                part_id=self.part_id,
                correct=self.correct,
                value_id=self.value_id1,
                answer_value=self.answer_value,
                problem_display_name=self.problem_display_name,
                question_text=self.question_text,
                variant=123,
                first_response_count=1,
                last_response_count=3,
                created=created,
            ),
            models.ProblemFirstLastResponseAnswerDistribution(
                course_id=self.course_id,
                module_id=self.module_id1,
                part_id=self.part_id,
                correct=self.correct,
                value_id=self.value_id1,
                answer_value=self.answer_value,
                problem_display_name=self.problem_display_name,
                question_text=self.question_text,
                variant=345,
                first_response_count=0,
                last_response_count=2,
                created=created,
            ),
        ]

        with patch('analytics_data_api.v0.views.problems.is_insights_snowflake_enabled', return_value=True):
            with patch(
                    'analytics_data_api.v0.views.problems.get_problem_answer_distribution',
                    return_value=snowflake_data,
            ) as mock_get_answer_distribution:
                response = self.authenticated_get(f'/api/v1/problems/{self.module_id1}{self.path}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Insights-Data-Source'], 'snowflake')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['variant'], None)
        self.assertTrue(response.data[0]['consolidated_variant'])
        self.assertEqual(response.data[0]['first_response_count'], 1)
        self.assertEqual(response.data[0]['last_response_count'], 5)
        mock_get_answer_distribution.assert_called_once_with(self.module_id1)

    def test_get_returns_404_when_snowflake_service_returns_no_data(self):
        with patch('analytics_data_api.v0.views.problems.is_insights_snowflake_enabled', return_value=True):
            with patch(
                    'analytics_data_api.v0.views.problems.get_problem_answer_distribution',
                    return_value=[],
            ) as mock_get_answer_distribution:
                response = self.authenticated_get(f'/api/v1/problems/{self.module_id1}{self.path}')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['X-Insights-Data-Source'], 'snowflake')
        mock_get_answer_distribution.assert_called_once_with(self.module_id1)


@set_databases
class GradeDistributionTests(TestCaseWithAuthentication):
    path = '/grade_distribution/'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.course_id = "org/class/test"
        cls.module_id = "i4x://org/class/test/problem/RANDOM_NUMBER"
        cls.ad1 = G(
            models.GradeDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id,
        )

    def test_get(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id, self.path))
        self.assertEqual(response.status_code, 200)

        expected_dict = GradeDistributionSerializer(self.ad1).data
        actual_list = response.data
        self.assertEqual(len(actual_list), 1)
        self.assertDictEqual(actual_list[0], expected_dict)

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEqual(response.status_code, 404)


@set_databases
class SequentialOpenDistributionTests(TestCaseWithAuthentication):
    path = '/sequential_open_distribution/'
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.course_id = "org/class/test"
        cls.module_id = "i4x://org/class/test/problem/RANDOM_NUMBER"
        cls.ad1 = G(
            models.SequentialOpenDistribution,
            course_id=cls.course_id,
            module_id=cls.module_id,
        )

    def test_get(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % (self.module_id, self.path))
        self.assertEqual(response.status_code, 200)

        expected_dict = SequentialOpenDistributionSerializer(self.ad1).data
        actual_list = response.data
        self.assertEqual(len(actual_list), 1)
        self.assertDictEqual(actual_list[0], expected_dict)

    def test_get_404(self):
        response = self.authenticated_get('/api/v0/problems/%s%s' % ("DOES-NOT-EXIST", self.path))
        self.assertEqual(response.status_code, 404)
