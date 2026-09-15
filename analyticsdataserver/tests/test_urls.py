from django.test import TestCase
from django.urls import reverse


class UrlConfigurationTests(TestCase):
    def test_admin_url_is_exposed(self):
        self.assertEqual(reverse('admin:index'), '/admin/')

    def test_admin_requires_authentication(self):
        response = self.client.get(reverse('admin:index'))

        self.assertRedirects(response, '/admin/login/?next=/admin/')
