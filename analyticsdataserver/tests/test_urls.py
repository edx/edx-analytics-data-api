from django.test import SimpleTestCase
from django.urls import reverse


class UrlConfigurationTests(SimpleTestCase):
    def test_admin_url_is_exposed(self):
        self.assertEqual(reverse('admin:index'), '/admin/')
