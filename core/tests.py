from django.test import TestCase, override_settings


@override_settings(ROOT_URLCONF="core.urls", ALLOWED_HOSTS=["cloudd1.com"])
class CsrfFailureTests(TestCase):
    def test_expired_token_redirects_to_a_fresh_form(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post("/accounts/login/", {}, secure=True, HTTP_REFERER="https://cloudd1.com/accounts/login/", HTTP_HOST="cloudd1.com")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "https://cloudd1.com/accounts/login/")
