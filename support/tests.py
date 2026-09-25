from django.test import TestCase
from django.urls import reverse

from .forms import SupportRequestForm
from .models import SupportRequest


class SupportRequestSecurityTests(TestCase):
    def form_data(self, **overrides):
        data = {
            "name": "Jane Member",
            "email": "jane@example.com",
            "subject": "Wallet question",
            "message": "Please help me with my wallet balance.",
            "website": "",
        }
        data.update(overrides)
        return data

    def test_rejects_script_and_template_payloads(self):
        for payload in ("{{7*7}}", "<script>alert(1)</script>", "javascript:alert(1)"):
            form = SupportRequestForm(self.form_data(message=payload))
            self.assertFalse(form.is_valid())
            self.assertIn("message", form.errors)

    def test_honeypot_rejects_bots(self):
        form = SupportRequestForm(self.form_data(website="https://spam.example"))
        self.assertFalse(form.is_valid())
        self.assertIn("website", form.errors)

    def test_rate_limits_requests_from_one_connection(self):
        url = reverse("support:request")
        for _ in range(3):
            response = self.client.post(url, self.form_data())
            self.assertRedirects(response, url)
        response = self.client.post(url, self.form_data())
        self.assertContains(response, "Too many support requests", status_code=200)
        self.assertEqual(SupportRequest.objects.count(), 3)